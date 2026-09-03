# Gate evidence ledger

**Every phase advance in darkmem is a measured number, not a judgement.** This file is
where those numbers live. A gate is cleared when its row here carries a real measurement,
its artifact path, and a verdict — not when someone believes the work is done.

## The rules

1. **State the bar before the run.** A bar written after seeing the number is not a bar.
   Every bar lives as a `config` row or a harness constant with a stated default.
2. **Accuracy never ships without its twin.** Any accuracy figure recorded here is
   accompanied by p95 latency and token cost. A row missing its twin is incomplete
   evidence, not a pass (doc 17 §2).
3. **A miss is recorded, not retried away.** If a number lands below its bar, write it
   down and leave the gate open. Never re-run until it passes; never widen a bar to fit a
   result. The gate working is the system working.
4. **Per-slice numbers are never collapsed.** A flattering aggregate hiding a collapsed
   slice is the dishonesty the whole harness exists to prevent.
5. **Every entry names its artifact.** A number with no reproducible artifact is an
   anecdote.

## Status

| Gate | Guards | Status | Cleared on | Evidence |
|---|---|---|---|---|
| G-A | Phase 0 → 1 | **CLEARED** | 2026-07-27 | T0.17 — this file, "G-A verdict"; `docs/eval/2026-07-27-T0.17-ga-evidence/`; `docs/eval/2026-07-27-retrieval-eval.md` |
| G-B | Phase 1 → 2 | **CLEARED** | 2026-07-28 | T1.50 — this file, "G-B — VERDICT"; `docs/eval/2026-07-28-retrieval-eval.md`; `docs/eval/2026-07-28-T1.24f-whole-chain-parity.md`; `backend/scripts/benchlib/run_isolation_probe.py` |
| G-C | L2 → deriver; Phase 2 exit | **CLEARED** (T2.131, on the grown corpus sha `78dbc4c5c8756dcd`, 849 captures: every pre-stated axis clears in both passes — 509 in-window corroborations, Clopper-Pearson 95% upper bound **0.009286** vs the 0.01 bar, all `gate_fired` buckets powered and clearing, 0 journal-completeness violations over 682 facts, every bar at its committed default. Verdicted by an independent party that recomputed every axis and reproduced the run byte-identically at 0 live calls; `promotion_metrics_record.json` minted on that verdict, so promoted and born fact statuses now reach readers. **What the clear does not license is part of the result**: every capture, origin, repo and the single dispute were authored by the measured party, the deterministic detector has never fired on an unauthored contradiction, the human-rejection arm has never met a human, and the `time_gap` path exists only under the harness's simulated clock — see "G-C on the grown corpus". The audit's arms were **re-derived, not merely re-run** (T2.111): the machine arm is judge-free, so the G-C→G-D critical-path edge recorded 2026-08-07 does not hold as written) | 2026-08-16 | T2.131 — this file, "G-C on the grown corpus"; `docs/eval/2026-08-16-gc-evidence-t2.131-pass{1-unsimulated,2-simulated}.md`; `docs/planning/reviews/2026-08-16-t2.131-gc-independent-verdict.md`; `backend/app/services/promotion_metrics_record.json`. Prior: T2.111 — "G-C re-measure"; T2.40 — "G-C verdict" |
| G-D | L2 → L3 | **CLEARED on the entailment role** (owner ruling 2026-08-17). T2.125 measured both roles on T2.124's fresh gold, pairs `4748ac84960fed67`, 280 live pairs, judge `gpt-5.5` identity `fd39e7b2c47fa375`: entailed precision **0.9906**/0.95, entailed recall **0.9545**/0.90, `contradicted → entailed` **0**, 0 invalid. The **contradiction role FAILS and stays open** — recall **0.7875** vs an unmoved 0.95, the fourth miss across two vendors — and gates only the Tier-C scan, which since T2.109 is not a veto input and so certifies no label G-D guards. No bar moved and the failed role's consumer stays dark. **Independence is dented and disclosed**: the judge had met 114 of the 280 measured pairs in two prior blind sittings on this gold and all three of its known disagreements were retired before the run; the worst-case restoration still clears at recall 105/113 = **0.9292** vs 0.90, so no verdict moves. The 2026-08-12 expiry check is live to **2026-11-12**. Note the record reaches production only with this branch's merge and the next deploy — G-D clearing and a grounded label being served are two events. See "G-D on the fresh gold" and "G-D ruling (2026-08-17)" | 2026-08-17 | T2.125 — this file, "G-D on the fresh gold", "G-D ruling (2026-08-17)", "The repair round"; `docs/eval/2026-08-17-judge-qualification-fd39e7b2.md`; `backend/app/services/verification_qualification.entailment.json`; `docs/planning/reviews/2026-08-17-t2.124-branch-review.md`. Prior: T2.114 — "G-D final attempt"; T2.41 — "G-D verdict", "G-D resolution" |
| G-E | L3 → F7 | **DEFERRED pending real usage data** (owner, 2026-08-18). Not a miss and not cleared: the instrument is ready and the corpus is not. Both bars were stated 2026-08-11 by derivation and owner-ratified before any coverage number existed anywhere — runtime threshold **0.95**, corpus share **0.90** — and T3.24's runner is `done`. What is absent is the thing no code produces: production holds **0 rows in `knowledge_articles`**, so a T3.22 run would spend the attempt to measure an empty corpus. It becomes runnable only after articles exist in production, which needs real capture or a driven research loop plus the ladder's ≥ 7-day origin spacing. Note `article_synthesis` was dead on arrival until 2026-08-17 (see the schema-drift analysis), so corpus growth could not have started before that date regardless. See "G-E" | — | T3.22 (todo); `docs/planning/analyses/2026-08-17-production-schema-drift.md` |
| G-F | core → H1 | **CLEARED 2026-09-03** — all four probes settled. Faithfulness **0.9825**/0.95 precision and **0.9333**/0.90 recall after the premise-framing repair (the 2026-08-17 miss of 0.888 was an instrument defect: 12 of 14 false-accepts cited spans that assert nothing — markdown `[ ]` checklist items and `Expected:` directives — while the shared prompt told the judge its premise was "a stored fact"). Both stability probes PASS on a bar stated before the runs and clarified under owner delegation; maintainer appetite stated. **Two disclosures ride with the clear and are not footnotes**: the faithfulness number is a repaired instrument measured against the gold that exposed it, with the one-re-measure stopping rule spent and independence never established; and the gold is agent-authored and agent-labelled with CLAUDE.md contamination reported by every participant. A first independent confirmation on a fresh span gold is owed. Two claims in the 2026-08-17 entry — "six strengthened claims" and `structure-fragment` "mixed" — were false and are corrected in "G-F re-measured" | 2026-09-03 | TH1.10 — this file, "G-F measured", "G-F re-measured on the repaired premise framing", "G-F stability probes measured", "G-F's three open probes"; `docs/eval/2026-08-17-th1.10-faithfulness-gate-run.log`; `docs/eval/2026-09-03-gf-remeasure-span-prompt.log`; `docs/eval/2026-09-03-gf-stability/`; `docs/planning/analyses/2026-09-03-gf-premise-framing-defect.md` |
| G-G | target → H2 | **closed** (entry conditions unmet) | — | — |

---

## G-A — Phase 0 → 1

**Owning task:** T0.17. **Bar lives in:** a harness constant (there is no hosted CI —
the gate is a scripted discipline, doc 17 §9).

Three probes, all of which must hold:

| Probe | Bar | Measured | Twin | Artifact | Verdict |
|---|---|---|---|---|---|
| Extraction F1 bench reproduces the recorded as-is baseline (entity name+type F1, relations F1) | Reproduce T0.05's recorded numbers | **All 8 cells reproduced exactly** — gold ent_nt 0.925 / ent_n 0.955 / rel_full 0.865 / rel_pair 0.892; held-out 0.893 / 0.929 / 0.667 / 0.667 | n/a (deterministic, zero model calls) | `docs/eval/2026-07-27-T0.17-ga-evidence/` | **PASS** |
| Retrieval eval runs with accuracy + p95 latency + token cost | Runs and reports all three columns | Pooled **MRR 0.8582 / hit@10 0.8431** over 102 pairs (7 slices); p95 end-to-end **2.43 ms** (cache-served); tokens: retrieval **unknown** (94 usage-less cache entries), full-context **472,558 prompt / 3,899 completion** over 102 calls | full-context arm: MRR 0.9069 / hit@10 0.9314 | `docs/eval/2026-07-27-retrieval-eval.md` | **PASS** (2 caveats) |
| Baseline migration boots clean; boot-time reconciliation idempotent | Clean boot; second boot is a no-op | Clean boot to 36 relations; 8 child tables; second boot a no-op (8→8); one dropped child regrown exactly (7→8) | n/a | `docs/eval/2026-07-27-T0.17-ga-evidence/boot.txt` | **PASS** |

### G-A verdict: **CLEARED** (2026-07-27)

**All three probes hold.** Doc 20 §4's rule is that no layer advances on
intuition; each probe below is a measured number with its artifact, and the two
caveats the harness raised are recorded rather than absorbed.

**Probe 1 — PASS, exact.** `run_bench.py --algo-only` over the restored T0.05
cache reproduced all eight cells of the recorded baseline byte-for-byte on both
`gold.json` and `gold_heldout.json`. Tolerance for this probe is 0 (it is
exact-match from a warm cache, not a live re-measurement), and it was met with
**zero live model calls** — `--algo-only` raises rather than calling out if any
output is uncached. Cache restored from the committed archive
`docs/eval/2026-07-26-T0.05-extraction-baseline-cache/` (36 files).

**Probe 2 — PASS, with two caveats that must not be lost.** The eval ran end to
end with **zero live LLM calls** (ingest 0, retrieval 0, full-context 0) and
reported all three columns. Accuracy and token figures reproduced the T0.09/T0.10
run **byte-identically**; only latency, the run id, the git sha and the gate-config
label differ, which is exactly the subset the runner's reproducibility contract
declares variable. The two caveats are the twin working as designed, not
shortfalls hidden in prose:

- `latency-no-live-samples` — **every** end-to-end sample in both arms was
  cache-served, so the p50/p95 figures describe a warm replay of a recorded run,
  not a system anybody runs. The latency column is present and honest about what
  it is; it is **not** a production latency measurement.
- `cost-unmeasured` — the retrieval arm's 94 extraction calls replayed from cache
  entries carrying no usage envelope. Read that as **unknown, never zero**, and
  never as this arm being cheaper. The two arms' token blocks are also different
  *kinds* of quantity: full-context bills one call per scored pair (recurring per
  query set), retrieval's 94 are one-time indexing work amortised over every
  future query, and retrieval's own per-query cost is 102 query-embedding calls
  that carry no token accounting at all. **Do not subtract or ratio them.**

**Probe 3 — PASS.** A database built from the single baseline revision alone
reaches 36 relations on a clean boot. The boot-time reconciliation created 8
child tables for a registered fingerprint; a second boot with a *fresh registry
object* (the restarted-process shape) left the count unchanged at 8, and dropping
one child then booting again regrew exactly that one (7 → 8), which is the
self-healing doc 19 §6 relies on for a restored dump.

**Two measured results that are headroom, not failures.** Recorded here so Phase 1
inherits them as facts rather than rediscovering them:

1. **Full context beats retrieval on pooled accuracy** — ΔMRR **+0.0487**,
   Δhit@10 **+0.0882** (full-context minus retrieval). G-A's bar does not require
   the retriever to win, and stating this plainly is the point of the T0.09
   comparator. It is the gap E1's pushdown and E2's graph arms exist to close.
2. **multi-hop hit@10 = 0.0000 on the retrieval arm is the DESIGNED state**
   (T0.06a), not a defect: every live multi-hop pair is built so its consequence
   memory ranks worse than k in the hybrid-only baseline. Per-slice, `temporal`
   is the one slice where retrieval *beats* full context on hit@10 (1.0000 vs
   0.6667).

**Backend floor at the time of this run:** 622 passed, 1 skipped, 0 failed against
a database built from the baseline alone; `alembic history` at exactly one
revision; `./scripts/gate.sh` green across all seven floor gates (alembic
single-revision, backend pytest, frontend typecheck, frontend test, frontend
build, benchlib tests, F1 bench `--algo-only`), including 276 benchlib tests and
336 frontend tests.

**Defect this run found, now fixed.** The eval could not even import before this
task: `benchlib/ingest.py` imported `MLProfile`, which T0.12c deleted, and
`pyproject.toml` sets `testpaths = ["tests"]` so the backend floor never collects
`scripts/benchlib/tests` and never saw the break. Migrated
`GateConfig.ml_profile_ref` → `classifier_kind` (the re-homing doc 04 §7 describes
and `ingest.py`'s own docstring predicted), added `classifier_kind` to
`LLMPurposeConfig`, and carried it through `get_llm_config`. **`scripts/gate.sh`
now runs the benchlib suite**, so a baseline-shaped change cannot break the harness
again with the floor still green.

**Phase 1 opens.** E1 may be entered. Carried forward as G-B's inheritance: the
two Tier-2 gaps already logged against the T0.05 baseline (no latency/token twin
on the extraction numbers; "same model" asserted rather than verifiable), plus
the `cost-unmeasured` caveat above — which together mean **T1.17's cost-based
justification for the merged one-call design still has no baseline twin to compare
against.**



**Recorded as-is baseline (T0.05)** — the reference every later phase compares against:

| Dimension | Gold P / R / F1 | Held-out P / R / F1 |
|---|---|---|
| Entity, name only | 0.985 / 0.928 / 0.955 | 1.000 / 0.867 / 0.929 |
| Entity, name + type | 0.954 / 0.899 / 0.925 | 0.962 / 0.833 / 0.893 |
| Relation, pair only | 0.943 / 0.846 / 0.892 | 0.846 / 0.550 / 0.667 |
| Relation, full triple | 0.914 / 0.821 / 0.865 | 0.846 / 0.550 / 0.667 |

**Stated G-B parity tolerance:** (set in T0.05, 2026-07-26, before Phase 1 starts;
floors recalibrated to substitution arithmetic the same day, after adversarial
review, before any Phase-1 number exists) — one-sided (a rise never fails), per
dimension (never aggregated, rule 4), on F1, measured with the same model and
seeded stack as this baseline. The unit is the **item flip** — one gold item lost
from a dimension's counts with a wrong item appearing in its place (a
substitution: tp−1, fn+1, **fp+1**). Substitution is strictly the worst
single-item move (a pure loss leaves fp unchanged and costs less, so it is
covered a fortiori), and it is the dominant failure shape in this very baseline
(e8/e15/e21/e22, h7/h8 are all substitutions or rewrites). The flip is the unit
because F1-per-flip spans ~4× across the eight cells (0.015 on gold entities to
0.061 on held-out relations), so a flat absolute-F1 tolerance would be
simultaneously loose on gold entities and hollow on held-out relations.
**Allowance: 3 flips per dimension**, decomposed as:

- **1 flip — re-measurement noise.** A warm-cache
  `--algo-only` re-run reproduced both outputs byte-identically — measured drift of
  the deterministic passes + scorer over the cached raw outputs is exactly 0, which
  is the G-A reproduction path. Vendor-side stability at a fixed prompt rests on the
  content-derived seed (documented, and verified reachable with `seed` by the
  controller on 2026-07-26 — not re-paid here; a second live pass per gold file is
  forbidden). The 1 flip is a judgement guard for the one uncontrolled source: a
  silent vendor-side model update between this baseline and the G-B run.
- **2 flips — T1.17's planned prompt change (judgement, stated as such).** Phase 1
  merges classification into the extraction call and strips the prompt to
  schema + content + seed + minimal rules (doc 05 §6; the stripping is tagged
  rebuild). That invalidates the whole cache (the prompt is in the key) and
  re-samples every raw output. The deterministic passes' contract (T1.24a–f) is to
  recover *systematic* losses, so this budget deliberately does **not** subsidise a
  degraded port — it covers only irreducible borderline re-rolls: items the raw
  model may drop under an altered prompt that no post-processing pass can rescue (a
  pass cannot invent an unmentioned entity). This run's diffs show that class is
  real (type-flips on "phoenix v2" in e8/e15; "design doc" missed in both gold e17
  and held-out h8). Its magnitude cannot be measured until the merged prompt
  exists; 2 flips is the stated judgement.

Floors — each of the 3 flips taken as a substitution against the frozen tp/fp/fn
above. Substitution keeps the denominator of F1 = 2·tp / (2·tp + fp + fn)
constant (−2 from tp, +1 each from fn and fp), so the conversion is exactly:

    floor = 2·(tp − 3) / (2·tp + fp + fn)

and each flip costs exactly 2 / (2·tp + fp + fn) in F1. A dimension passes at
F1 ≥ its floor — landing exactly on the floor is a pass, since the floor *is*
the granted 3-flip budget spent in full. Worked per cell (a future agent should
recheck this arithmetic, not trust it):

| Dimension | Gold floor = 2(tp−3)/(2tp+fp+fn) | Held-out floor |
|---|---|---|
| Entity, name only | 122/134 = **0.910** | 46/56 = **0.821** |
| Entity, name + type | 118/134 = **0.881** | 44/56 = **0.786** |
| Relation, pair only | 60/74 = **0.811** | 16/33 = **0.485**\* |
| Relation, full triple | 58/74 = **0.784** | 16/33 = **0.485**\* |

\* The held-out relation slice holds only 20 gold relations, and its baseline
misses are cascade-dominated: h3 alone is 6 of the 9 fns, all downstream of three
missed root entities, so one borderline *entity* re-roll lands on these cells
multiplied by its fan-out. The starred cells therefore carry a **one-way cascade
valve** — it can pass a run that breaches the floor; it never fails a run that
holds it:

- At or above the 0.485 floor: pass, no triage. This is exactly the 3-flip
  budget, no stricter.
- Below the floor: the G-B ledger entry must include the `--diffs` triage, and
  the run passes only if **both** conditions hold:
  1. **Recall side — exactly one root accounts for every new miss.** New misses
     are gold relations missed at G-B that are not among this baseline's 9 fns,
     grouped by **root**: a root is the missing or type-flipped entity (subject
     or target) shared by new misses; a new miss whose endpoints are both
     correctly extracted is its own root. One borderline entity re-roll
     amplified by fan-out is still one item in the budget's own unit; two or
     more roots is systematic relation loss and fails, whatever the F1. **Zero
     new misses also fails** — the valve exists for recall cascades, and a
     below-floor drop with no new miss is precision-driven by construction:
     with the frozen counts, 22/(31+fp) < 16/33 requires fp ≥ 15, i.e. ≥ 13
     new spurious, which condition 2 rejects anyway. Stating the verdict closes
     both the vacuous reading ("every new miss" true over an empty set) and the
     literal one.
  2. **Precision side — at most 3 new spurious relations.** New spurious are
     predicted-but-not-gold keys at G-B that are not among this baseline's 2
     spurious (`ruff -USES-> mypy` in h9 and `rfc 9114 -CITES-> raft paper` in
     h8; their pair projections likewise), counted from the same `--diffs`
     `REL SPUR` lines the triage already prints. The bound is identity-aware —
     a baseline spurious that disappears frees no slot — and 3 is the same
     amplitude the unstarred budget grants (3 substitution flips add at most
     fp+3): the valve widens the tolerance only on the recall side, never on
     precision.

The valve is one-way and unbounded only in *recall* amplitude, on purpose: the
load-bearing relation bar is the gold slice (39 gold relations, no valve), these
cells are an overfit alarm whose signal is *independent* new misses rather than
the size of one cascade, and a cascade's root entity is still charged to the
entity dimensions' own floors, which have no valve. Boundary reconciliation: the
valve engages only below the floor, so it can never fail a run the 3-flip budget
passes; and a run it passes differs from a budget-pass only in the fan-out of
one recall cascade — its precision allowance is the budget's own. Note also that
the valve pardons *narrower* cascades than the one that motivated it: h3, the
baseline's dominant cascade, has three roots (`cli`, `mobile app`, `web app`)
and would fail the valve if it recurred as new misses. That is consistent — two
or more roots is the systematic signal regardless of provenance — but it should
not have to be rediscovered at G-B.

Scope: this tolerance judges G-B's live re-measurement under the Phase-1 prompt.
G-A's reproduction probe is exact-match from the warm cache (`--algo-only`, zero
model calls, tolerance 0). Not comparable across models: the 2026-07-22
cerebras/gpt-oss-120b numbers (ent_nt 0.941 / rel_full 0.923 on gold, darkmem
memory `3de71b1c`) are a different model's; this baseline is deepseek-v4-flash's,
and G-B must be measured with the same model.

**Recorded gap — rule 2's twin is absent (Tier-2, logged 2026-07-26).** The eight
accuracy figures above come from 36 live calls with no p95 latency and no token
cost. `run_bench.py` does not instrument either; that instrumentation is T0.08's
deliverable and was out of bounds for T0.05, so the twin is missing rather than
omitted silently. Consequence to carry forward: T1.17's cost-based justification
for the merged one-call design has **no baseline twin here to compare against at
G-B**. The probe row's "n/a (deterministic, zero model calls)" covers only the
reproduction probe, not this live block.

**Recorded gap — "same model" is asserted, not verifiable (Tier-2, logged
2026-07-26).** The cache stores only the parsed extraction JSON — no response
`model` string, no system fingerprint — and `deepseek-v4-flash` is a vendor alias
whose backing weights can rotate silently. The noise component's vendor-update
guard is therefore not falsifiable against this baseline; at G-B, "silent vendor
update" must not be accepted as an explanation for a shortfall unless the G-B
runner captured response metadata showing what was actually served (requirement
recorded under G-B below).

Run context: git sha `a63675c515c88ea7089bf911dc68389e9dcc86dd`, model
`deepseek-v4-flash` (`api_kind=deepseek`, `https://api.deepseek.com/v1`, seeded
into `darkmem_bench` by `benchlib.run_smoke.seed_llm_purpose_configs`, key from
`DEEPSEEK_API_KEY`, empty params so vendor-default temperature, content-derived
seed forwarded), fingerprint: extraction-prompt sha256[:16] = `775ca7c45ed9a06a` —
sha256 over the prompt text alone, truncated to 16 hex, identifying the prompt
revision (the per-entry cache key is `sha256(content + "\x00" + prompt)[:16]`; the
prompt hash is not itself a key component). The bench embeds nothing, so no
embedder fingerprint applies. Date 2026-07-26. Artifact: the 36 raw-output files
archived at `docs/eval/2026-07-26-T0.05-extraction-baseline-cache/` (committed);
working copy `backend/scripts/extraction_bench/.cache/` (machine-local,
gitignored). To restore the working copy for the G-A reproduction probe, copy the
archive's `*.json` back into the `.cache/` directory.

Verbatim output — `run_bench.py` (gold.json), live, 2026-07-26:

```
================ PER-MEMORY (entity F1 / relation F1) ================
  e1    ent=1.00  rel=1.00
  e2    ent=1.00  rel=1.00
  e3    ent=1.00  rel=1.00
  e4    ent=1.00  rel=1.00
  e5    ent=1.00  rel=1.00
  e6    ent=1.00  rel=1.00
  e7    ent=1.00  rel=1.00
  e8    ent=0.50  rel=1.00  <--
  e9    ent=1.00  rel=1.00
  e10   ent=1.00  rel=1.00
  e11   ent=1.00  rel=1.00
  e12   ent=1.00  rel=1.00
  e13   ent=0.67  rel=1.00  <--
  e14   ent=0.86  rel=0.80
  e15   ent=0.50  rel=1.00  <--
  e16   ent=1.00  rel=1.00
  e17   ent=0.80  rel=0.00  <--
  e18   ent=0.80  rel=0.67  <--
  e19   ent=1.00  rel=1.00
  e20   ent=1.00  rel=1.00
  e21   ent=0.86  rel=0.50  <--
  e22   ent=1.00  rel=0.00  <--
  e23   ent=1.00  rel=0.00  <--
  e24   ent=0.80  rel=1.00
  e25   ent=1.00  rel=1.00
  e26   ent=1.00  rel=0.00  <--

================ AGGREGATE (micro) ================
  Entity (name+type)               P=0.954 R=0.899 F1=0.925   (tp=62 fp=3 fn=7)
  Entity (name only)               P=0.985 R=0.928 F1=0.955   (tp=64 fp=1 fn=5)
  Relation (s,TYPE,t)              P=0.914 R=0.821 F1=0.865   (tp=32 fp=3 fn=7)
  Relation (s,t) type-agnostic     P=0.943 R=0.846 F1=0.892   (tp=33 fp=2 fn=6)
```

Verbatim output — `run_bench.py --gold gold_heldout.json`, live, 2026-07-26:

```
================ PER-MEMORY (entity F1 / relation F1) ================
  h1    ent=1.00  rel=1.00
  h2    ent=1.00  rel=1.00
  h3    ent=0.57  rel=0.00  <--
  h4    ent=1.00  rel=1.00
  h5    ent=1.00  rel=1.00
  h6    ent=1.00  rel=1.00
  h7    ent=0.80  rel=0.80
  h8    ent=0.80  rel=0.00  <--
  h9    ent=1.00  rel=0.00  <--
  h10   ent=1.00  rel=1.00

================ AGGREGATE (micro) ================
  Entity (name+type)               P=0.962 R=0.833 F1=0.893   (tp=25 fp=1 fn=5)
  Entity (name only)               P=1.000 R=0.867 F1=0.929   (tp=26 fp=0 fn=4)
  Relation (s,TYPE,t)              P=0.846 R=0.550 F1=0.667   (tp=11 fp=2 fn=9)
  Relation (s,t) type-agnostic     P=0.846 R=0.550 F1=0.667   (tp=11 fp=2 fn=9)
```

---

## G-B — Phase 1 → 2

**Owning task:** T1.50. **Bar lives in:** a harness constant + `config`.

| Probe | Bar | Measured | Twin | Artifact | Verdict |
|---|---|---|---|---|---|
| Extraction F1 parity with the recorded baseline | Within the T0.05 tolerance | gold **0.912 / 0.971 / 0.883 / 0.883** (floors 0.881 / 0.910 / 0.784 / 0.811); held-out **0.967 / 0.967 / 0.950 / 0.950** (floors 0.786 / 0.821 / 0.485 / 0.485) — all 8 cells clear, cascade valve not engaged. Reported as the T1.24f decomposition, never a headline (verdict section below) | recorded gap stands: the T0.05 baseline itself has no latency/token twin; the live re-record's usage is in the Pass-B cache entries | `--algo-only` at `16f8fb0` over `docs/eval/2026-07-28-T1.17-merged-prompt-cache/`; arithmetic in `docs/eval/2026-07-28-T1.24f-whole-chain-parity.md`; verbatim output in the T1.50 report | **PASS** (2026-07-28, T1.50) |
| Retrieval eval vs full-context baseline | Reported with twin; no silent regression | Per-slice accuracy byte-identical to G-A on all 7 slices; pooled retrieval MRR 0.8582 / hit@10 0.8431 vs full-context 0.9069 / 0.9314. Post-T1.17 baseline re-established: 94 live merged-prompt extraction calls paid this run | p95 end-to-end 0.00303 s retrieval / 0.00023 s FC (cache-served, caveat recorded); tokens: retrieval indexing **927,166 prompt / 11,661 completion, live-measured**; FC 472,558 / 3,899 per query set — different kinds, never subtracted | `docs/eval/2026-07-28-retrieval-eval.md` (run `6b7b0c0d`, git `16f8fb0`) | **PASS** (2026-07-28, T1.50) |
| Isolation probe: unlabelled cross-project or superseded rows, **every** channel | **Exactly 0** | **10** (2026-07-28, T1.35), then **0** (2026-07-28, T1.35a), re-measured **0** at `16f8fb0` (2026-07-28, T1.50, `darkmem_bench_1`) with per-surface row widths identical to the failing run | n/a (deterministic, zero model calls) | `backend/scripts/benchlib/run_isolation_probe.py` (output below and in the T1.50 report) | **PASS; the 10 stands recorded** |

**Requirement recorded by T0.05:** the runner producing this gate's live F1
re-record must capture and record response metadata (the served `model` string
and any vendor system fingerprint) alongside its cache. The T0.05 baseline's
cache carries none, so model identity is only checkable from the G-B side; a
shortfall attributed to a vendor-side model update is admissible only with that
metadata recorded (see the "same model" gap under G-A).

**Isolation probe detail** (T1.35, measured 2026-07-28) — a single leaked row
fails the gate. **Measured: 10 violations. This probe row is a FAIL and G-B
stays open** (rule 3: recorded, not retried away).

**The metric, stated before the run** (in code: `benchlib/isolation_rules.py`,
whose module docstring is the bar's definition). A violation is a returned row
of memory-derived data (full content, preview, or write-echo) that is either
**V1** — outside a scope the request carried (explicit project/status
parameter, a scope derived from the addressed row, repository id, or the
active-fingerprint constraint); labels never excuse a V1 — or **V2** — a
cross-project or non-active row on a legitimately wide read (operator-wide
surface, or a ratified every-project default) that does not itself carry the
labels naming its true project / lifecycle state (Ruling 5: a labelled
superseded row is the design; an unlabelled one is the count). Two exposures
are **reported but deliberately not counted**, with the decision stated per
Ruling 4: **id-only exposure** (`memory_ids` arrays, crossrefs, relation
edges — T1.29d/e parked these as an open product question; 15 observed) and
**retention snapshots** (append-only journal/citation content outliving its
memory — escalated to the human by T1.29e; 3 observed). The channel inventory
is `app.services.content_surfaces.CONTENT_SURFACES` (never a doc's list —
Ruling 1); the probe aborts if any registry surface lacks a driver, and every
raw response body is sentinel-scanned so a row crossing through an
unenumerated field is a forced V1, not a pass.

Per-channel result — the five originally tabled channels first, then the
surfaces the registry adds (rule 4: never collapsed):

| Channel / surface | Cross-project leaks | Superseded leaks | Verdict |
|---|---|---|---|
| Semantic (search REST+MCP, projection, unified, duplicates) | 0 | 0 | PASS |
| Keyword (FTS arm + relational fallback arm) | 0 | 0 | PASS |
| Graph (memory-context neighbours, entity browser) | 0 | 0 | PASS (id-only exposure reported, not counted) |
| `memory_reason` (REST + MCP doors) | **4** | 0 | **FAIL** |
| Code search (REST + MCP, both arms, cross-repo + cross-fingerprint) | 0 | 0 | PASS |
| Chat retrieval (`/chat/completions` sources) | **2** | 0 | **FAIL** |
| Re-embed backfill queue (`/reembed/obsolete/memories`) | **1** | **1** | **FAIL** |
| Chat history citations (persisted snippets) | **2** | 0 | **FAIL** |
| Pipeline-failure triage | 0 | 0 | PASS (wide, labelled) |
| Analytics recents | 0 | 0 | PASS (wide, labelled) |
| Capture-buffer triage | 0 | 0 | PASS |
| Event journal (3 doors) | 0 | 0 | PASS (retention reported, not counted) |
| Memory by id / write echo | 0 | 0 | PASS |
| Content-free-route sweep (34 GET doors) | 0 | 0 | PASS |

**The ten leaked rows, named** (full output reproducible via
`cd backend && BENCH_DATABASE_URL=... python scripts/benchlib/run_isolation_probe.py`):

1–2. `memory_reason` REST, default every-project scope (ratified): two
   `iso-beta` rows returned as 200-char content previews in `sources` with
   **no project or status key on the row** — the response shape carries
   `memory_id/content/score/tags` only.
3–4. `mcp:memory_reason`, same shape, same two rows.
5–6. `chat_retrieval`, default context: two `iso-beta` rows land in the
   `sources` SSE event (full content) with no labels.
7. `reembed_backfill_queue`: a cross-project row previewed 120 chars with no
   labels (items carry `memory_id` + `content_preview` only).
8. `reembed_backfill_queue`: a superseded row, same unlabelled shape.
9–10. `chat_history_citations`: the two beta rows from leak 5–6 persisted as
   150-char snippets, re-served unlabelled on every conversation read.

**Registry-honesty finding (Ruling 2).** The registry rows for
`memory_reason` and `chat_retrieval` declare `labels=("project", "status")`,
but neither response shape emits those keys on its rows — the label claim
describes the internal SQL, not what the surface returns. The
`reembed_backfill_queue` row honestly declares `labels=()`, which under this
bar is precisely why its wide rows count. Fixing any of this is **not** this
probe's job (a probe that fixes what it measures cannot be trusted to measure
it); the fixes need owners before this probe can be re-run for the gate.

**Instrument evidence.** Deterministic: two consecutive full runs produced
byte-identical reports (10 violations, exit 1). Zero model calls by
construction — the orchestrator stub has no HTTP client. Sensitivity proven
by mutation: removing the status clause from `MemoryFilter.where_sql` drove
the count 10 → **58** with named V1 status-breach rows on every
semantic-backed channel; restoring it returned exactly 10. Hostile fixtures
cover: superseded rows with live successors, an entity asserted by memories
in two projects, archived rows, rows embedded only under an inactive
fingerprint (never served — verified), rows missing from the active
partition, the absent-partition degradation (enumeration withheld, count
exact — verified), and journal/citation content outliving a deleted memory.
What passed is itself evidence: every T1.29a–e pushdown held under these
fixtures, including both code-search arms and the graph neighbour status
predicate.

**Re-measurement after T1.35a (2026-07-28): 0 violations, exit 0.** The ten
above were closed by labelling, not by narrowing — every one of them was a
`[V2]` unlabelled escape rather than a wrongly returned row, and all four
surfaces are still exactly as wide as they were. The per-surface row counts in
the re-run are identical to the failing run (`memory_reason` 16,
`chat_retrieval` 8, `chat_history_citations` 9, `reembed_backfill_queue` 3);
only the V2 column moved to zero, which is the evidence that no row was
removed to make the number. The informational I1/I2 lists are unchanged and
remain out of scope (T1.60 and the escalated retention question).

The labels are stamped at the point the rows are produced, following T1.29d's
`get_all_vectors` precedent: `PostgresVectorRepository.search` and both
`HybridSearchService` arms now join `memories` unconditionally and emit
`project` + `status` on every row, so a consumer nobody enumerated still gets
labelled rows; `MemoryService.reason` builds one citation shape for both its
passes and therefore for both doors; `ChatService` labels the `sources` event
and the persisted citation snapshot; the re-embed queue labels its previews.
The registry-honesty finding is closed in the direction the bar requires: the
false statements were the `memory_reason` and `chat_retrieval` *responses*, and
those were fixed rather than the classification relaxed. `reembed_backfill_queue`
and `chat_history_citations` now declare `labels=("project", "status")` because
they now emit them.

The probe, its fixtures and its predicates were not touched. Guard tests live
in `backend/tests/test_scope_labels.py` (18); each labelling point was mutated
in turn and the corresponding tests observed failing before restoration.

---

## G-C — L2 → deriver; Phase 2 exit

**Owning task:** T2.40. **Bar lives in:** `config` rows over committed defaults —
`backend/scripts/benchlib/promotion_bars.py` (`PROMOTION_BAR_DEFAULTS`, pinned by value in
`scripts/benchlib/tests/test_promotion_bars.py` so a moved bar is a two-file diff, never a
quiet constant tweak). **Metrics computed from the `events` journal by SQL** — an
unjournaled transition is an unmeasurable one.

**Bars stated 2026-08-07, before any gate run** (T2.40; the G-D rows are the precedent
for this recording). The bar module also commits, ahead of any count, the two
definitional rulings that decide what the audit counts: **R1** — a citation-driven
downgrade (T2.48) is a `demote`, never a false promotion (the audit measures promotion
precision, not repository churn; boundary case of promoted-on-already-stale-citation
stated and bounded by one reverify tick); **R2** — the T2.101 fact fold can move a
journaled corroboration's identity out from under a later dispute when the keeper's rung
was unjournaled (born-corroborated), so the audit **undercounts** in exactly that shape —
anti-conservative, therefore every measurement reports the in-window fold count beside
the audit; **R3** — `_write_born_rung`'s two unjournaled writes (deriver birth, and the
post-dispute restore, which IS a `candidate → corroborated` change that journals nothing
on doc 10 §6's licence) are the completeness probe's one carve-out, counted and reported,
never silently absorbed.

| Probe | Bar | Measured | Artifact | Verdict |
|---|---|---|---|---|
| Promotion rate `(promoted / eligible)`, sliced by source-kind diversity | Every powered bucket ≥ 0.5 (`promotion_rate_floor`); axis decidable only with ≥ 1 powered bucket (eligible ≥ 5, `promotion_rate_min_eligible` = the harness's own `UNDER_POWERED_THRESHOLD`) **and** ≥ 1 journaled `promote` in window (`promotion_rate_min_promotions`); stated 2026-08-07, before any gate run | **0 eligible, 0 promotions** on both targets (window 2026-05-09 → 2026-08-07): production `darkmem` journal holds 0 `verified` events; bench corpus (62 facts through the shipping lift + recompute) journaled 0 transitions — every fact is a single anonymous origin (`origin_key` NULL on all 62 `fact_sources` rows, folded to the reserved bucket, which counts once and can never fire a gate), so nothing can meet N. Axis not decidable under the pre-stated predicate | `docs/eval/2026-08-07-promotion-metrics.md` (production probe, the task's Verify); `docs/eval/2026-08-07-t2.40-gc-evidence/` (bench run + corpus structure); reproduce: `run_promotion_metrics.py`, `run_gc_evidence.py` | **UNDER-POWERED — not evaluable; gate stays open** |
| Promotion rate, sliced by which N fired | Same bar family, same keys, per bucket; under-powered buckets reported with denominators, never collapsed, and can neither clear nor fail; stated 2026-08-07, before any gate run | Same numbers, same window, same two targets: 0 eligible in every bucket on both axes (`gate_fired` buckets empty) | same | **UNDER-POWERED — not evaluable; gate stays open** |
| False-promotion audit (corroborated later disputed or human-rejected) | Rate **< 0.01**, strict (`verification_false_promotion_bar`, doc 17 §5.1's own key and recommended start); decidable only at ≥ 20 in-window distinct corroborated facts (`false_promotion_min_corroborations`) — below 100 corroborations one false promotion already breaches 1%, so within the decidable band the bar demands zero observed; stated 2026-08-07, before any gate run | 0 corroborations, 0 disputed-after, 0 human-rejected, rate n/a on both targets; R2's fold count in window: **0** `expired` fact events. **Structural finding:** both numerator arms are unreachable today — the contradiction scan aborts on the unqualified judge (no qualification record until T2.54 → T2.41), and the review queue only fills from disputes/blocked holds, so even a corroborating corpus would yield a *vacuous* zero, not a measured one | same, plus `contradiction_scan.py`'s one-door refusal (its module docstring) and `verification_judge.QUALIFICATION_RECORD_PATH` absent | **UNDER-POWERED — not evaluable; and not honestly evaluable before the judge qualifies (see verdict)** |
| Every ladder transition journaled | 100% (`promotion_journal_completeness_bar` = 1.0): zero `knowledge_triples` rows whose `verification_status` the `verified` journal cannot explain, per `promotion_bars.JOURNAL_COMPLETENESS_SQL` (committed with the bar, before any run); R3's born-rung carve-out counted and reported beside the number; stated 2026-08-07, before any gate run | Production: 0 facts, 0 violations (vacuous). Bench: **62 facts, 0 violations, 0 born-rung carve-out rows** — every row's column state is journal-explained, but 0 transitions occurred, so 100%-of-transitions is 0/0. The behavioural evidence that transitions journal is `tests/test_ladder_journaling.py` (mutation-pinned), which is test evidence, not corpus evidence | same; SQL committed in `promotion_bars.py` | **CONSISTENT BUT VACUOUS — cannot evidence the 100% bar; gate stays open** |

### G-C on the grown corpus (2026-08-16, T2.131): **CLEARED** — every pre-stated axis clears, independently verdicted, record minted

The owner authorised the run on 2026-08-16, conditioned on closing the owed
review's two open findings first (both closed: `6d0453d1`, `7a2f9801`). Corpus
sha256 `78dbc4c5c8756dcd`, 849 captures — a new corpus, not a re-run of
`2840651b597da347`. Both passes ran, unsimulated first as the plan binds.

| Metric | Pass 1 (unsimulated) | Pass 2 (simulated clock) |
|---|---|---|
| Bench lane | `darkmem_bench_t2131` | `darkmem_bench_t2131sim` |
| Live model calls | **913** (extraction 849) | **0** — replayed from pass 1's cache |
| Wall clock | 303.11s | 45.84s |
| In-window corroborations | **509** | **528** |
| Later disputed / human-rejected | 1 / 0 | 1 / 0 |
| False-promotion point estimate | 0.0020 | 0.0019 |
| **95% Clopper-Pearson upper bound (SCORED)** | **0.009286** vs 0.01 → clears | **0.008953** vs 0.01 → clears |
| `gate_fired` eligibles | [363, 147] — diversity, none | [363, 146, 20] — diversity, none, time_gap |
| Diversity-arm conversion, as the instrument prints it | 364/365 = 0.9973 | 365/365 = 1.0000 |
| Diversity-arm conversion, **authored claims only** | 363/365 = **0.9945** | 363/365 = **0.9945** |
| `none`-arm conversion (no instrument prints this) | 144/145 = **0.9931** | 144/145 = **0.9931** |
| Journal completeness | 682 facts, 74 carve-out, **0 violations** | identical |

All four axes report `clears=True` in both passes, on bars every run printed as
committed defaults: the measured databases carry **no `config` row for any G-C
bar and no `promotion_bar_licences` row**, so nothing was moved, clamped or
licensed. The corpus was sized against a 0.9703 diversity conversion and
delivered 0.9973, which is why 509 landed above both the 473 requirement and the
490 self-imposed floor rather than near them.

**What actually changed, stated precisely.** The audit's problem was never the
point estimate — T2.130 established that comparing an estimate to the bar it is
centred on is a coin flip at *every* sample size, and this run reproduces that
diagnosis rather than escaping it: pass 1 prints P(pass | true rate = bar) as
**0.6001** under the superseded rule and **0.0369** under the scored one. What
moved is that 149 corroborations could not clear the bound at zero observed,
and 509 clears it at one observed. The k = 1 numerator is unchanged; the
denominator is what grew.

**The designed refusals and controls held in both passes.** `avro` (under-sourced,
2 origins) and `cassandra` (echo, 1 origin over 3 provenance rows) both stayed
`candidate`; the `warehouse` inverse-replacement pair disputed as designed with
`corroborated_first=True` on the counterpart; the only superseded rows sit inside
the `scheduler` blocked-hold group, and the arming project reads 0.

**The simulation dependency, measured rather than asserted.** Pass 1 disables the
capture-time stamp, and the `time_gap` bucket does not shrink — it is **absent**,
its 20 promotions and 18 `atlas` facts staying `candidate` at two same-day
origins. That is the T2.129 finding reproduced on the grown corpus: one of G-C's
three gate paths exists only under the harness's simulated clock. The pass that
carries the target is therefore pass 1, and it clears without that path.

**§6's disclosure, written before the number existed and quoted here as Step 6
requires.** A cleared bound at ~500 makes the audit **decisive about a corpus its
own measurer wrote**: one authored dispute over ~500 authored corroborations.
The composition is concentrated — diversity claims cannot leave project `default`
(`fact_lift.CODE_FACT_PROJECT`), so `default` holds 365 of the 509 promoting
claims, against one stand-in repository fleet of six. A reader meeting
"509 corroborations, bound 0.009286, clears" must meet in the same breath that
every one was written to be counted. T2.130's limit is unlifted: a well-powered
rule over authored evidence is a better instrument measuring the same thing, and
this task sharpened the instrument without widening what it can see.

**Step 5's independent verdict: CLEARED** — recorded 2026-08-16 by a party that
neither authored the growth nor ran the passes, which is the requirement's whole
point. It recomputed every axis with its own SQL against both measured
databases, reproduced the run end to end in its own lane
(`darkmem_bench_t2131verify`, 0 live calls, byte-identical on every gate number),
audited the bars through `git` rather than through the run's own print (unchanged
since `57f07d52`, 2026-08-07, before any measurement), and confirmed R2's fold cap
at 0 expired events. Full report:
`docs/planning/reviews/2026-08-16-t2.131-gc-independent-verdict.md`.

**It answered the denominator-honesty question the task text called the real
risk, and the corpus passed**: 849 memories share **156** distinct origin keys
(max reuse 20), the code kind has exactly 6 origins, and there are zero
anonymous, blank or `unknown:*` origins — so "one assertion relabelled 473
times" is not what happened.

**Two claims in an earlier draft of this section were overstated and are
corrected above rather than quietly dropped.** (1) The **`none` arm did not
convert at 1.000**: basalt authored 22 claims and 21 corroborated, because
`bs-h3` produced **no fact at all** — no `h3` entity was ever extracted. True
conversion 144/145. The running session reported 1.000 from a hand-count that
mis-attributed a `default` fact to that arm, and **the runner prints no `none`
reconciliation**, so nothing was watching — the silent shape plan §7 predicted.
(2) The **diversity aggregate is inflated by unauthored promotions**: the
instrument counts any promoted fact whose subject is a fleet repo name, so
`merchant-portal USES dashboard` — nobody's claim, promoted on the `none` gate —
counts as a diversity conversion, which is how pass 2 prints 1.0000 while the two
known authored misses still failed. Authored-claim conversion is 363/365 in both
passes. Structurally the instrument can mask a real authored miss 1:1 against a
noise promotion.

**Neither correction moves the verdict.** Two of the 509 corroborations are
undesigned; stripped, the bound still clears at 507 → 0.009322 (pass 2:
526 → 0.008987). One non-determinism is disclosed rather than smoothed: pass 1
printed `scheduler superseded=1 of 3`, pass 2 and the reproduction print `2 of 3`
— the known T2.129 Phase-5 race, confined to the blocked-hold group, arming
project 0 everywhere.

**On the strength of that verdict the gate owner minted
`app/services/promotion_metrics_record.json`** (2026-08-16). Promoted and born
fact statuses now reach readers; the badge is lit by an evidence record, not by
a code change, which is the T2.95/T2.100 design. The record names the corpus sha,
both passes, the scored rule and the independent verdict that licensed it.
**What it does not license is recorded beside it**, in the reviewer's words as
well as §6's: the detector has never fired on an unauthored contradiction, the
human-rejection arm has never met a human, and the kind diversity carrying 363 of
the 509 promotions means the same hand wrote the assertion twice in two formats.
Artifacts: `docs/eval/2026-08-16-gc-evidence-t2.131-pass1-unsimulated.md` and
`…-pass2-simulated.md`, verbatim.

### G-C bench-arm evidence run (2026-08-13): **NOT CLEARED — operable and powered for the first time, and still not clearable**

The first G-C verdict driven from T2.108's promotion corpus (`--corpus
promotion`, corpus sha `9c74f451b0cbfa14…`, unchanged since `b33cee39`). Both
prior measurements read the empty production journal; this run finally puts
facts through the counting ladder and reports powered denominators on every
probe. Report and untrimmed transcripts:
`docs/eval/2026-08-13-gc-bench-evidence/`. Reproduce:
`run_gc_evidence.py --corpus promotion` against a fresh
`darkmem_bench_gc`, both with and without `--no-capture-time-simulation`.
**The decision rule was stated in the report before either pass ran**: no
numeric outcome could clear this run, on grounds already on this ledger.

**Measured (window 2026-05-15 → 2026-08-13; 66 captures, 42 facts through
the shipping lift; fingerprint `qwen3-embedding:0.6b|1024`):**

- **Rate by `gate_fired`** — pass 1 (simulated capture clock): diversity
  **11/11**, none **10/10**, time_gap **10/10**; all powered (≥ 5), all clear
  the 0.5 floor at 1.000. Pass 2 (`--no-capture-time-simulation`): diversity
  11/11, none 10/10, **time_gap bucket empty** — its 10 promotions rest
  entirely on the one disclosed simulation; the other two buckets are
  byte-identical without it.
- **Rate by diversity** — diverse 11/11, homogeneous 20/20 (pass 2: 10/10).
- **False-promotion audit** — 31 corroborations (pass 2: **21, decidable by a
  margin of one** over the 20 floor), 0 disputed-after, 0 human-rejected,
  rate 0.0000; **R2 fold companion: 0** `expired` events in window.
  `audit_clears` printed True in both passes and **that True is the vacuous
  reading the 2026-08-07 amendment predicted, now observed in a real gate
  run** — all three numerator producers verified dark on this run's data:
  0 stored REPLACES-family edges (SQL over `entity_relations`, so
  `inverse_replacement` could not arm; `SINGLE_VALUED_RELATIONS` still
  empty), 0 `human_verdict` events, and the LLM scan never ran, dead-ends on
  the unqualified judge, and post-T2.109 could not mint a dispute anyway.
- **Journal completeness** — 42 facts, 0 violations, **1 born-rung carve-out**
  (`payments-gateway USES python`, code-only provenance, R3's licence, named
  not absorbed). **Non-vacuous for the first time**: 31 (21) transitions
  occurred and every one is journal-explained, so the claim is "100 % of
  counting-ladder transitions journaled, 1 born-rung row excluded".
- **Both designed refusals refused for the designed reasons** —
  `ledger-exports USES avro` held `candidate` (2 same-kind origins < 7 days,
  k=2 against N=3); `ledger-core USES cassandra` held `candidate` (1 origin
  behind 3 provenance rows). Identical in both passes.
- **Bars in force** — the T2.128 block printed the explicit no-rows sentence
  ("the measured database carries no `config` row for any G-C bar and no
  `promotion_bar_licences` row: every bar below is its committed default,
  unmoved"), and was **verified against the database rather than believed**
  (its author built it): independent SQL found 0 rows for the six bar keys
  and the licence key; the committed/effective pairs match
  `PROMOTION_BAR_DEFAULTS`. No misreport.
- **Live calls, disclosed** — the promotion cache was empty on this machine,
  so pass 1 made **73 live round-trips** (seeded `deepseek-v4-flash`
  extraction for 66 captures plus embedding chunks), unlike T2.108's
  cache-served `live_calls: 0`; pass 2 replayed the warm cache at 0.
  Extraction drifted under the live pass — 42 facts vs the reference 38 —
  and **every drifted fact landed as a single-origin `candidate`**:
  promotions bucket-for-bucket identical, controls byte-identical. The
  gate-relevant structure survived a fully live re-extraction.
- **Twin (rule 2):** pass 1 35.9 s wall / 73 live round-trips; pass 2
  14.6 s / 0. Token counts are **not measurable from this harness** (the
  cache stores response text only) — a recorded gap for a future powered
  run, not an omission.

**Verdict: NOT CLEARED — gate stays open; no record minted.** The run
demonstrates the bench arm end-to-end and retires "under-powered" as the
reason: every probe now has denominators. What it cannot do is clear:
the audit's clear is vacuous with its numerator's producers verified dark,
the owner ruling the 2026-08-07 amendment demands is unmade, and the
verdict section's route (b) carries a judge-qualification precondition G-D
(open) does not meet. `promotion_metrics_record.json` stays absent; every
promoted or born badge keeps serving as `candidate` with
`verification_unmeasured`; the deriver-lane consequence is unchanged.

**The brief's Tier-3 question, answered rather than left ambient:** the
bench arm *can* carry a G-C verdict — this ledger's own "What would evaluate
this gate" clause (b) says so, and doc 17 §11's sequencing makes it the only
pre-cutover route, so "primary target" (production) and "only pre-cutover
route" (bench) state preference and availability, not a contradiction. No
gate-definition change was needed to record this NOT CLEARED. **Recording
CLEARED from this arm would be a gate-definition act, and it is escalated to
the gate owner, not settled here**, as three open items: (1) rule on the
vacuity amendment — what makes a zero-numerator audit *measured*? (noting
T2.108's review result that no corpus in the 20–99 corroboration band can be
both operable-numerator and passing under the strict 1 % bar, so the defect
attributes to the bar); (2) whether a route-(b) clear licenses minting the
promotion record — production badges lighting on corpus-design evidence —
or the mint waits for a route-(a) production window; (3) if the bench route
is to become clearable, the arming path for the audit's machine arm (a
REPLACES-family corpus extension arms `inverse_replacement` judge-free, at
the cost of item 1's band problem; the human arm needs G-D plus a reviewer
no harness run can supply).

### G-C arming, passes 1 and 2 (2026-08-14, T2.129): the audit's machine arm is **operable** for the first time

Executing the owner ruling above — grow the census past 100 and arm the machine
arm, with the 1% bar unmoved (rule 3). Corpus sha `2840651b597da347`; pass 1 ran
at `4449a3b447bf8684`. Both are new corpora, not re-runs of `9c74f451b0cbfa14…`.

**Pass 1 armed the detector and still measured a numerator of 0.** The census
half worked — 148 corroborations against a floor of 20, all three `gate_fired`
buckets powered and clearing, both designed refusals intact — and the detector
produced a real judge-free dispute on live rows under `inverse_replacement`. But
the subject fact never journaled `corroborated`: its three wave-1 memories each
assert one REPLACES edge in one project, so `detect_supersessions` retired each
under the next and `supersession_hold` withheld the promotion. The fact held at
`candidate` with `supersession_blocked` journaled — in the eligible denominator,
never the numerator — and the dispute landed with nothing to join. **The zero
was still inoperability, not precision.** Recorded red at `9b7d2283`.

**Pass 2 closed it, and the repair was five dates.** Every arming capture moved
150 days back, outside `SUPERSESSION_WINDOW_DAYS`, so no supersession fires in
the arming project at all. Measured: **0** superseded rows in the project, **0**
anywhere in the database, **0** `supersession_blocked` events. The subject
promotes on its three wave-1 origins; the wave-2 counterpart then disputes it,
`corroborated_first=True` where pass 1 printed `False`.

| Metric | Pass 1 | Pass 2 |
|---|---|---|
| In-window corroborations | 148 | **149** |
| Later disputed | 0 | **1** |
| False-promotion rate | n/a (vacuous) | **0.0067** vs a 0.01 bar |
| `gate_fired` eligibles | [98, 34, 19] | [98, 33, 18] — all powered, all clearing |

**No bar, threshold or ladder predicate moved** — verified independently against
the pin test, both artifacts' bars-in-force blocks, and a config-row scan of the
measured database. **One harness predicate did move, and it costs something this
ruling asked for — recorded here because it was missed on the first write-up.**
`validate_arming_design`'s new window clause is enforced at every corpus load
against the live clock, so **the supersession-blocked hold is now structurally
unreachable in the arming groups for every admissible future corpus.** Pass 1
was the first measured window in which that hold fired — twice, on the armed
subject, with four superseded warehouse memories. The 2026-08-13 ruling above
made `blocked ≡ 0` reachable "until a veto **or a supersession-blocked hold**
actually fires in a measured window"; this repair delivers the veto arm and
forfeits the other, and the guard that protects the numerator is the same guard
that forecloses it. The blocked-hold evidence exists and is preserved (pass 1,
database `darkmem_bench_t2129run`) but is no longer reproducible under the
committed validator. **Whether that guard should be waivable — so a deliberate
blocked-hold corpus stays expressible — is an owner call this lane did not
take.**

**A pre-registration claim here was overstated and is corrected.** This
paragraph previously said the census deltas "were pre-stated in the plan before
the run and match". The plan pre-stated promotions 148 → 149 and pass 1's
vector, but its mechanism named **one** blocked hold where the journal carries
**two**; its own arithmetic yields 34 → 34, and the destination vector
[98, 33, 18] appears nowhere in it. That vector was discovered at run time. The
plan also cited `promotion_rate_min_eligible` = 20; **the bar is 5**, and the
"not spare slack" argument built on the wrong value was false. Both errors
entered through the Fable review and survived it. The plan was
Fable-reviewed before execution, and that review killed a wrong mechanism claim
(moving wave 1 alone would in fact have landed the numerator — `decide` checks
the veto ahead of every count and the already-corroborated branch returns before
`supersession_blocked` is read) and a wrong pre-stated denominator (148 → 149).
`validate_arming_design` now refuses an arming capture inside the window,
importing the bound from `app.services.relations`, with the failing side pinned
against a fixed clock because the pass-1 dates stop failing a live one around
2026-10-18.

**What this does not do, stated where the number lives.** It does **not** clear
G-C. It makes one arm of the false-promotion audit operable **as an instrument**
— the independent probe's distinction, and the right one: the arm is not
operable as evidence *about the system*, because the single number it produces
is authored end to end.

**The 0.0067 must not be quoted without its power.** A system whose true
false-promotion rate sits exactly **at** the failing bar passes this audit
**56% of the time** at n = 149 (`P(X ≤ 1 | n=149, p=0.01) = 0.5604`, verified
independently), and the exact 95% interval for 1/149 reaches ≈ **0.037**, about
3.7× the bar. "Decidable" is the protocol's term for n ≥ 20; it is not a claim
that the audit decided anything. The harness prints
`false-promotion audit: decidable=True clears=True` forty lines above the
caveats, which is the quotable hazard.

**The demonstrated state is not door-reachable.** `MemoryCreate` carries no
`created_at`, production `memories.created_at` is the ingest stamp, and
`detect_supersessions` anchors at ingest wall-clock — so three same-claim
captures 2–5 days apart *cannot* all survive `active` in production; each ingest
retires the previous, which is precisely what pass 1 demonstrated. Pass 2's
state exists only because the harness backdates attribute-side. The nearest
production analogues are different shapes (re-assertions genuinely ≥ 90 days
apart, or a Phase-5 re-extraction > 90 days after capture emitting REPLACES
edges the original ingest missed) and neither is what was shown. The earlier
"disjoint-window case only" wording read as though the pass-2 shape were one of
the production shapes; it is not.

Further limits: the numerator is **one fact**; every promotion-rate bucket reads
1.000 because the corpus was authored to promote, so those probes confirm design
and measure nothing; pass 2 ran at `live_calls: 0` — the cache memoises
embed/chat on content plus purpose config, so it would have succeeded with both
vendors dark, and **every model output behind this graph, including the REPLACES
edges the arming rides on, is vouched for by pass 1's single live run made by
this corpus's own author**; and neither pass carries the latency/token twin the
2026-08-13 G-C run recorded under rule 2, a reporting regression against this
ledger's own precedent.

**The independent evidence re-run T2.129's done-when owes has now been done**
(2026-08-14, by a party that did not build the corpus, chartered adversarially).
It reproduced the run byte-identically from committed state on its own database,
re-derived every figure by its own SQL, verified pass 1's failure story on the
preserved database, and confirmed the guard bites both ways. Its verdict: the
measurement half is sound and **G-C should not clear**. Every finding above
except the two corrections is its work. Artifacts:
`docs/eval/2026-08-14-t2.129-arming/`.

### G-C blocked-hold reachability restored (2026-08-14, T2.129 follow-on): both of the ruling's arms now fire in one measured window

The subsection above records that pass 2's window clause made the
supersession-blocked hold "structurally unreachable in the arming groups for
every admissible future corpus", forfeiting one of the two arms the
2026-08-13 ruling names, and escalated "whether that guard should be
waivable" as an owner call. **The repair taken does not answer that question
— it moots it**: the guard is not waivable and did not move (the clause still
iterates the arming groups alone, its tests unchanged and green); a seventh
corpus group, `blocked_hold`, carries the hold in a project of its own.
Three sessions assert one replacement (`dagster REPLACES oozie`, project
`scheduler`), deliberately dated **inside** the window, so ingest retires
each capture under the next and the ladder journals the meets-bar-but-held
decision. Waivability was rejected because it weakens the guard to a
convention and still cannot produce both arms in one window; standing on
pass 1's preserved database was rejected because that evidence is not
reproducible from committed state (the committed validator refuses its
corpus, and after ~2026-10-18 no live-clock run could reproduce it at all),
because the two arms would still never have fired in one window, and because
it would leave `blocked ≡ 0` in every future corpus forever — so a
regression in the hold's journalling would be invisible to every future G-C
run. Report and full alternatives argument:
`docs/eval/2026-08-14-t2.129-blocked-hold/report.md`, corpus sha
`69dbb717b0476167`, run database `darkmem_bench_t2129hold`.

**That database no longer holds the run, and nothing here rests on it**
(verified 2026-08-14, after the lane reported). The lane ran the full harness
suite against the same database *after* its evidence run; the DB-backed tests
reset the schema, so the measured state was destroyed by its own verification
step. `darkmem_bench_t2129hold` now holds two rows from a unit-test probe.
**The committed artifacts are the evidence and are intact** — which is the
whole reason a run is written to `docs/eval/` rather than left in a database.
Contrast pass 1, whose database `darkmem_bench_t2129run` *is* still readable
and was re-read by the independent probe: that reproducibility is not available
here, so this run is evidenced by its artifact alone. A future party wanting
the live rows must re-run from committed state; the corpus sha and the
pre-registration make that a re-derivation rather than a re-authoring.

**Measured, against a pre-registration committed before the run**
(`fbae980c`). The numerator path reproduced pass 2 exactly: promotions 149
(98/33/18 by gate), audit 1/149 = 0.0067 with `corroborated_first=True`, R2
companion 0, 0 superseded memories in the arming project. The restored arm:
2 of 3 `scheduler` memories superseded, the fact held at `candidate` with
origins = 3, **2** `supersession_blocked` hold events journaled — bucket
`none` reads promoted 33 / blocked 2 / eligible 35, rate 0.943, powered and
clearing. No bar, threshold or ladder predicate moved; every bars-in-force
row reads "no config row; the committed bar stands".

**One pre-stated point estimate was wrong, recorded here as this ledger
recorded the pass-2 plan's identical genus of error.** The pre-registration
expected exactly 1 hold event (pass floor ≥ 1) and the run journaled 2. Both
rows read `k=3 n=3 candidate→candidate blocked=true`, and the parameterized
invariant (eligible = 33 + B, B ≥ 1, fact never promoted) held; the eligible
vector [98, 35, 18] under B = 2 was not pre-stated as a point.

**The mechanism this ledger first gave for the extra hold was wrong, and the
journal disproves it** (independent probe, 2026-08-14; verified here against
two preserved databases). It said the fact's three `sources_changed` events
"straddled the recompute drain's 100-event batch boundary, so two consecutive
ticks each re-decided the fact". They did not straddle anything: in
`(created_at, id)` order those events sit at ranks **255, 256, 257** — wholly
inside one 100-event batch. The real mechanism is the **slow arm on tick 1**:
`slow_arm_last_run_at` is unset on a fresh database, so the first tick sweeps,
and `DEFAULT_SLOW_BATCH` = 200 covers all 175 facts. The journal shows it —
**150 `verified` rows share one transaction stamp** (149 promotions *and* hold
#1), with hold #2 alone at a later stamp as the fast arm reaches batch 3.
Pass 1's preserved database carries the identical signature (149 rows at one
stamp, hold #2 alone later), so the clause "the same accounting that gave pass 1
two holds" repeated the wrong mechanism for pass 1 as well.

**This is the failure the pre-registration discipline exists to catch, and it
half-failed.** The miss was disclosed rather than buried — that part worked —
but the surprise was then explained by a mechanism inferred rather than derived,
checkable from timestamps the lane itself quoted, and wrong. The lane then
destroyed its database, which is what made the claim uncheckable until an
independent re-run. **A disclosed miss with a fabricated explanation is worse
than an undisclosed one**, because it reads as understood.

**What this buys — corrected 2026-08-14, the first wording was false about the
instrument.** It said "both producers of `blocked > 0` — the veto and the
supersession-blocked hold". **The veto is not a producer of `blocked`.**
`_PROMOTION_RATE_BY_GATE_SQL` counts `blocked` from
`(payload->>'supersession_blocked')::boolean` alone; a veto firing from
`candidate` produces a **dispute**, which enters *eligible* and never `blocked`,
and a contradiction-blocked hold carries `before='disputed'` and is excluded
from the metric entirely. Empirically in this run, `contradiction_blocked=true`
appears on exactly the two dispute rows and on no hold. Under the committed SQL
**the supersession hold is the only producer of `blocked`.** What the window
actually demonstrates is veto → *disputes* and hold → *blocked*, which is what
the 2026-08-13 ruling asked for on its literal terms — its own "a veto or a
supersession-blocked hold" wording conflates the two, and this ledger amplified
that into a claim about the metric. Corrected rather than quietly reworded,
because the false version reads as stronger instrument coverage than exists.

The hold's journalling (the T2.60 shape `_PROMOTION_RATE_BY_GATE_SQL` counts)
does have standing regression coverage in every future evidence run.

**A metric-design question this raises, for the gate owner.** The hold count
`B` is a *scheduling artifact*, not a corpus property: a supersession-blocked
fact journals a hold on **every** recompute visit, the hold never lifts, and the
slow arm revisits every non-confirmed live fact on a 600-second cadence. `B = 2`
here only because the run finishes in ~30 seconds. Over a long measured window a
single permanently-held fact accrues holds roughly linearly (~144/day at the
default cadence), inflating that bucket's per-transition eligible denominator
without bound — enough, on a small vault, to sink the 0.5 promotion-rate floor
as pure artifact. **The promotion-rate probe is therefore not yet a stable
instrument for a production-length window**, and that is a bar-and-metric
question to settle before G-C is measured against one. The blocked-hold group is also the
one corpus state reachable through a capture door: `MemoryCreate` carries no
`created_at` and `detect_supersessions` anchors at ingest wall-clock, so
three same-claim captures days apart cannot all survive `active` in
production — pass 1's shape, now expressed deliberately instead of by
accident.

**What it costs, stated where it will be read.** The corpus is no longer a
fully absolute timeline: the group's dates are spelled `now-<N>d` and
resolve against the run clock at load (the loader refuses an absolute date
in this group — a silent 90-day fuse — and a relative date anywhere else),
so two runs on different days write byte-different `created_at` rows in the
`scheduler` project while the corpus sha and every design property stay
fixed. The run made 6 live calls (the three new contents), so the group's
extraction is vouched for by its own author's single live run — the same
caveat pass 1 carries for everything else. And the blocked demonstration is
instrument-operability only: a corpus authored to be held confirms the
mechanism, not the system's behaviour.

**What this does not do.** It does not clear G-C, does not mint the record,
does not touch the audit's power caveats (the 56 %-at-the-bar figure and the
one-fact numerator stand as written above), and is not certified by the lane
that built it — the independent evidence re-run T2.129's done-when owes
remains owed and now covers this corpus too.

### The unsimulated pass: one of G-C's three gate paths is a property of the simulation (T2.129, 2026-08-14)

The `--no-capture-time-simulation` run T2.129's done-when has owed since pass 1,
on the same corpus (`69dbb717b0476167`) so the clock is the only variable.

| | simulated | unsimulated |
|---|---|---|
| corroborations | 149 | **131** |
| `gate_fired` eligibles | [98, **35**, 18] | **[98, 35]** |

**Units corrected 2026-08-15 (T2.129's final-commit review, I-2).** The left cell read `[98, 33, 18]` under an *eligibles* label, and 33 is the **promoted** count — the simulated run's eligibles were `[98, 35, 18]`, its own artifact says so, because the 2 blocked holds were already in that denominator. Mixing promoted into an eligibles row understates the very denominator the blocked-hold group was built to populate. The `time_gap`-disappears conclusion survives either reading, and the wrong figure propagated to the commit message and the task row.

**The `time_gap` bucket does not shrink — it disappears.** All 18 of its
promotions exist only under the simulated clock, exactly as `promotion_corpus`'s
own docstring predicts: the gate reads `fact_sources.created_at`, which on any
single-pass backfilled corpus records the lift's write time rather than the
capture's. Two of G-C's three gate paths survive an honest clock; **the third is
a property of the harness**, and any future G-C verdict quoting three powered
buckets is quoting one the corpus cannot produce without help.

**What owes the simulation nothing:** the arming. The armed subject corroborates
on three distinct origins by count, so the numerator survives at 1 disputed, and
the blocked-hold arm still fires (`none` eligible 35 = 33 promoted + 2 holds).
Both surviving buckets stay powered and clearing.

**The audit, read both ways** — point estimate 1/131 = **0.0076**, 95% upper
bound **0.0357**, evidence supports a true rate under the bar: **NO**. Worth
noting as a live demonstration of T2.130: dropping 18 corroborations moves the
point estimate by 0.0009 and the bound by 0.0043. The point estimate is nearly
insensitive to how much evidence stands behind it; the bound is not.

**Disclosed, because the artifact contradicts a sentence above it (T2.129's
final-commit review, I-1, 2026-08-16).** The two runs differ where the clock
cannot reach: the simulated artifact records `scheduler superseded=2 of 3`, the
unsimulated one `superseded=1 of 3`. The blocked-hold design pre-registered
**exactly 2 of 3**, and its stated mechanism — each capture retired by the next
— did not reproduce. The clock cannot explain it: supersession runs at ingest
off `memories.created_at`, which the flag never touches, app code is identical
between the runs, and extraction was fully cache-replayed. The structural
suspect is a commit-ordering race — Phase-5 writes are concurrent
(`asyncio.gather` under a semaphore) and `detect_supersessions`' overlap guard
reads a sibling's `technologies`, which that sibling's own Phase-5 write
populates, so within the in-flight window the count can be 2 (oldest first), 1
(mixed) or 0 (newest first). **Three things follow, and none of them moves a
number.** The hold demonstration survives, because one superseded source
suffices to fire `supersession_hold` — 2 hold events, `none` blocked = 2,
unchanged, which is why every quoted figure still reconciles. But "the clock is
the only variable" is too strong as a description of these two runs and should
be read as "the clock is the only *intended* variable". And the harness's
mechanism claims are pre-registered against a quantity that is not
deterministic, so the two byte-identical reproductions of the simulated run
were partly luck. **What would settle it is a re-run of the unsimulated pass to
see whether the count flaps — and that re-run is not free on this machine**:
`backend/scripts/benchlib/promotion/cache/` is gitignored and absent, so the
pass would pay for its extraction calls rather than replaying them. Recorded
here rather than settled, with the alternative remedy named: an ordering
guarantee in Phase 5 for same-project REPLACES chains would make the
pre-registered 2 of 3 a property rather than an observation.

**Rule 2's twin is present for the first time in four runs** — 15.97 s wall, 0
live calls, extraction `cache_unknown=246`. The runner had never carried twin
instrumentation at all, which is why the ledger's notice of the omission never
fixed it. `promotion_corpus` now builds `TwinningOrchestrator` (a subclass, not
a fork: same cache, same keys, same replay semantics). `cache_unknown` is the
honest reading for entries written before usage capture existed — never coerced
to a paid zero. Artifact: `docs/eval/2026-08-14-t2.129-unsimulated/`.

### G-C's audit had almost no rejection power, and more data was never going to fix it (T2.130, 2026-08-14)

The audit's decision rule was **`observed rate < 0.01`**. Measured: a system
whose **true** rate sits exactly **at** the failing bar passes that rule about
half the time — **and at every sample size.**

| corroborations | P(pass \| true rate = the bar) |
|---|---|
| 149 | 0.5604 |
| 300 | 0.4221 |
| 1 000 | 0.4573 |
| 10 000 | 0.4865 |

**This is the correction that matters: growing the corpus does not repair it.**
Comparing a point estimate to the bar it is centred on is a coin flip at the
boundary by construction, so the pass probability converges to ~0.5 rather than
to 0. The independent probe's closing suggestion — that "roughly n ≥ 300" would
drop the at-the-bar pass probability meaningfully — is arithmetically false, and
the table above is the disproof. Every earlier statement in this ledger that
treats the census size as the audit's limiting factor was aiming at the wrong
quantity: **the defect is the decision rule, not the denominator.**

**What the audit now reports beside every rate** (`promotion_metrics.py`, pinned
by `tests/test_promotion_audit_power.py`): the exact one-sided **Clopper-Pearson
upper confidence bound** on the true rate, whether the evidence *supports* a
true rate under the bar, the at-the-bar pass probability under both rules, and
the window size that would settle it. Exact binomial arithmetic, no normal
approximation — the approximation is worst exactly where this audit lives, at
tiny rates and small counts.

**On the measured window, the honest reading is that it does not clear.**
1/149 is a point estimate of 0.0067 and a **95% upper bound of 0.0314** — over
three times the bar. n = 149 is in fact too small to clear the bound *even with
a perfect record*: zero false promotions in 149 still bounds only to 0.0199. The
derived window sizes are **299** corroborations at 0 observed, **473** at 1,
**628** at 2. These are consequences of the bar rather than a stated floor,
which is what `false_promotion_min_corroborations` = 20 never was.

**The proposed rule change, for the owner: score the audit on `upper bound <
bar`.** It is **strictly a tightening** — the bound is never below the point
estimate, so no window that clears the new rule fails the old one, and under
this ledger's floors discipline a tightening needs no licence. Its at-the-bar
pass probability is bounded by 1 − confidence = **0.05** by construction, and it
still passes a genuinely good system: at n = 1000 a true rate of 0.002 clears
**94.8%** of the time. **This lane has not switched the verdict** — the scored
rule is unchanged and the new numbers are printed beside it, because changing
what the gate *decides* is the owner's, and doing it silently inside a
power-reporting change is exactly the move this ledger exists to catch.

**What this does not fix.** Power is not the only thing wrong with the audit:
the numerator is still one authored fact, the corpus is still authored by the
measured party, and a `blocked`-arm denominator still inflates with wall-clock
(recorded above). A well-powered rule over authored evidence is a better
instrument measuring the same thing. It buys honesty about what a "clears"
means, not a cleared gate.

**The proposal above was ruled on and taken — see the next section. The
paragraph saying "this lane has not switched the verdict" describes T2.130's
scope and stays true of it; it is no longer true of the tree.**

### The audit is scored on the bound (owner's ruling 2026-08-15, T2.132)

**The owner took T2.130's proposed switch.** `promotion_bars.audit_clears` now
scores the **95 % Clopper-Pearson upper bound** on the false-promotion rate
against the same 0.01 bar. **No bar moved**, and no licence is involved: the
bound is never below the point estimate, so this can only refuse windows the old
rule cleared — a strict tightening under this ledger's floors discipline.

**The predicate takes counts, not a rate, and that is not a refactor.** A rate
cannot be bounded after the fact. 1/149 and 20/2980 are both 0.006711; their
bounds are **0.0314** and **0.0097** — opposite verdicts from an identical
observation. The old signature could not express the rule, which is why the
stored ledger row now carries `upper_bound`, `confidence` and `scored_on`
beside `rate`: a row holding only the rate cannot be re-scored under the rule
that produced its own verdict.

**The consequence, stated where the number lives: the audit axis flips from
`clears=True` to `clears=False` on the corpus as it stands.** 1/149 bounds to
0.0314 against 0.01. This is the switch working, not a regression — the pass it
retires is the one T2.130 had already measured as worth approximately nothing,
and the axis it flips was the only G-C axis reporting a clear on a number this
ledger had itself disowned. **G-C did not clear before the switch and does not
clear after it.** No `promotion_metrics_record.json` was minted at any point, so
no served badge changes.

**It also settles what T2.131 is for.** That task's targets — 299 at zero
observed, 473 at one, the 490 floor it sized to — were derived from
`corroborations_required`, i.e. from the bound, while the gate was still scoring
the point estimate. So the corpus-growth route was aimed at a rule the gate did
not yet apply. It now applies it: reaching the target and clearing the audit are
the same event, where before they were two.

**A second bar became inert and is kept anyway.**
`false_promotion_min_corroborations` = 20 is **subsumed at the committed bars** —
the bound cannot clear 0.01 below 299 corroborations at any observed count, so
the floor refuses nothing the bound would have cleared. It is retained because
it still guards the empty window the bound cannot be computed for, still labels
`decidable` in the report, and becomes live again the moment the ceiling is
licensed upward, which is exactly the configuration an abuse of these bars would
reach for. Its clamp is therefore worth more than its current liveness suggests.
This is recorded rather than left to be discovered: a bar that decides nothing
while a table says it does is the same defect class as a stale count on a
"here is the full list" sentence.

**One repair to a claim this ledger relied on.** `promotion_metrics`' mirrored
copies of the bar and the confidence carried a comment reading "`promotion_bars`
remains the authority; a mismatch is caught by test", and **no test referenced
either constant**. That mattered little while the block was commentary; it
decides what a cleared run's report *says* now, so the mirror is pinned to
`PROMOTION_BAR_DEFAULTS` by test, and the rendered verdict is pinned to the
predicate's verdict across five windows. Found while making the switch, fixed
with it, recorded because the sentence had been load-bearing and false.

**What this does not buy, restated so the switch is not over-read.** The
numerator is still **one** fact, the corpus is still authored end to end by the
measured party, and the `time_gap` gate path still exists only under the
harness's simulated capture clock. A better-powered rule over the same evidence
measures the same evidence. Every limit recorded in the sections above survives
this change unchanged.

**The first landing shipped the defect it was closing, one layer up — found by
review, fixed, recorded here because the artifact is what this ledger quotes**
(`docs/planning/reviews/2026-08-15-t2.132-task-review.md`, Critical). Making the
audit block verdict-bearing left it computing its own answer: it compared the
bound against the module constant `_AUDIT_BAR_FOR_POWER` and **consulted no
decidability floor at all**, while `audit_clears` read both resolved bars. Three
reachable configurations diverged, every one an *honoured* `config` row — two
free tightenings and one valid licence:

| config row | artifact printed | gate actually scored |
|---|---|---|
| bar tightened to 0.005 | `→ CLEARS` (0/299) | **False** |
| decidability floor raised to 400 | `→ CLEARS` (0/350) | **False** |
| bar licensed to 0.05 | `→ does NOT clear` (1/149) | **True** |

So a ledger-quotable body could carry a line *claiming to be the scored rule*
asserting a pass the gate refused — the same two-resolutions class T2.128 closed
for the bar block, reintroduced by the change that exists to stop a verdict
reading cleaner than its evidence. **The author disclosed the bar channel in the
review brief and had not found the decidability channel or the reverse
direction.** Disclosure is recorded as what it was: incomplete, and not
mitigation.

**The fix removes the rule rather than aligning the two copies.** The renderer
now takes an `AuditVerdict` — the predicate's own answer plus the bar it was
scored against — and holds **no bar comparison of its own**, so divergence is
not guarded against but unspeakable. A caller that resolved no bars passes
nothing and the line renders **UNSCORED**, saying in the artifact that no bars
were resolved.

That default also repairs a contract broken outside the diff (review,
Important): `run_promotion_metrics.py` prints the same block against the
**production** database, resolves no bars, and its docstring promises it
"renders no pass/fail verdict" — true again, and now enforced by a test rather
than asserted in prose. Also fixed: the bound prints at six decimals, because
0.009969 (clears) and 0.010002 (fails) both rendered as `0.0100 against bar
0.01`, two identical lines with opposite verdicts.

**One test was coverage it did not provide.** `test_no_window_below_the_floor_can_clear_the_bound`
passed with `clopper_pearson_upper` stubbed to clear everything — every
below-floor refusal came from the decidability guard, never the bound its name
claimed. It now asserts the bound directly, and the "at *any* observed count"
half of the subsumption claim is pinned by a monotonicity-in-k test rather than
resting on an unstated property. The subsumption arithmetic itself was
independently re-derived in closed form by the review and holds exactly: 299.

### The corpus-growth route is taken, and its target is 490 — not the 300 that was suggested, and not the 473 first recorded here (owner instruction 2026-08-15, T2.131)

**The owner directed the lane down the independent probe's route — grow the
corpus — rather than the bound-rule switch T2.130 left open.** The route is
taken; the number came with it, and the number is wrong. Recomputed here with
the committed instrument (`promotion_metrics.clopper_pearson_upper`,
`at_bar_pass_probability`, `corroborations_required`), at the corpus's actual
**k = 1** observed false promotion:

| n | point estimate | clears the *then*-scored point rule? | 95% upper bound | clears the bound (**scored since T2.132**)? | at-bar pass (point rule) |
|---|---|---|---|---|---|
| 131 (today, unsimulated) | 0.0076 | yes | 0.03570 | no | 0.6227 |
| 149 (today, simulated) | 0.0067 | yes | 0.03144 | no | 0.5604 |
| **300 (as suggested)** | 0.0033 | yes | **0.01571** | **no** | 0.4221 |
| 400 | 0.0025 | yes | 0.01180 | no | 0.4325 |
| **473 (derived minimum)** | 0.0021 | yes | **0.00999** | yes, by 1×10⁻⁵ | 0.4884 |
| **490 (the floor)** | 0.0020 | yes | **0.00964** | **yes** | 0.4574 |
| **500 (what the route is sized to reach)** | 0.0020 | yes | **0.00945** | **yes** | 0.4396 |

**Three of the five-decimal bounds in this table were wrong when first written, and
the way they were wrong is worth recording** (re-review, M-v2-1). They were
four-decimal values with a fifth digit supplied by hand rather than by the
instrument, and the 490 row's at-bar figure was 473's copied down. Every figure
above is now machine-generated from `promotion_metrics`. Precision invented to look
rigorous is the same defect class as a number quoted without its `k`.

**Bounds are stated to five decimals here, and the reason is the 473 row.** At four
decimals it prints `0.0100` against a strict `< 0.01` rule — a tie rendered as a pass,
which is the exact shape this ledger exists to catch. **473 is the derived minimum and
a bad target**; the plan's working target is **490**, which bounds to 0.00964 and is
unambiguous in print. The bar did not move: a target acquired a margin.

**Where the 300 came from, and why it does not apply.** T2.130 derived 299 —
and that is the **k = 0** window. The suggestion carried it across to a corpus
that has k = 1, where the derived window is **473**. So the suggested growth
lands at a bound of 0.0157, over half again the bar, and changes no verdict.
Under the currently *scored* rule it changes even less: the at-the-bar pass
probability is non-monotone in n (0.4221 at 300, 0.5361 at 350, 0.4325 at 400)
because the admissible `k` steps in integers, so "more data" does not even move
it in a consistent direction.

**The trade-off this exposes is structural, and it is the finding worth
keeping.** The corpus has k = 1 *because* T2.129 armed it, and the arming is
what made the audit non-vacuous at all — T2.129's whole result is that an
unarmed zero means nothing. So the two properties price against each other: an
**unarmed** corpus settles at 299 and its clear is vacuous; an **armed** corpus
is meaningful and settles at 473. There is no window at which the audit is both
cheap and honest, and 299 is only ever the price of the vacuous one. Whoever
next quotes a required window must say which `k` it assumes.

**What the 473 costs, measured rather than estimated.** Today 246 authored
memories yield 131 unsimulated in-window corroborations. Reaching 473 needs
**+342 corroborations**. The only group that converts near one-for-one is
`diversity` (98 promotions from 101 memories, because the repo fixture supplies
the second origin of a second kind), which put the first sizing at **+350
authored captures plus their matching repo-fixture edges**.

**That sizing was optimistic, and the step-level plan written the same day says
why** (`docs/superpowers/plans/2026-08-15-t2.131-corpus-growth-to-473.md` §3.1).
It assumed the cheap arm scales, and it does not:
`validate_diversity_group_against_fixture` refuses two claims naming one
dependency — deliberately, since they would converge on one fact — and
`repo_fixture.json` carries a **single** repo. So +342 diversity claims means one
stand-in service repo with **443 distinct third-party dependencies**, which is not
a repository anyone could have indexed. The ceiling is plausibility, not effort,
and plausibility is the premise the corpus rests on. The realistic route is mixed
— multi-repo diversity (a loader change) plus `none` at ~2.7 captures each —
at **≈ +615 captures**, about 3.5× the corpus rather than 2.4×, on top of one
that already tripled under T2.129. **A second hazard scales with it**: any new
capture carrying a REPLACES-family relation arms a *second* dispute and moves the
target from 473 to 628, so the growth could outrun its own goal.

**Both of those paragraphs were corrected again the same day, by the plan's own
adversarial review, and the second was a refuted mechanism rather than a stale
number** (`docs/planning/reviews/2026-08-15-t2.131-plan-review.md`). Recorded in
place, because the sizing above has now moved twice and a reader arriving at the
first figure should not have to discover that by scrolling.

- **The sizing is ≈ +603 captures, and it took three passes to get there** —
  +350, then +582, now +603. Each correction moved the *conversion*, never the
  bar. `none` converts at **3.00 memories per claim** (96 → 32 by distinct
  `claim_key`), not the 2.7 from dividing by a `gate_fired` bucket carrying other
  groups' facts. The second pass then replaced that error with a *blended*
  constant, `131 ⁄ 133 = 0.985`, describing its two-claim gap as unexplained — and
  **the committed census refutes the premise**: the 131 is diversity **98 of 101
  (0.9703)** plus `none` **32 of 32 (1.0000)** plus the armed subject's one
  corroborated-then-disputed fact, which growth does not reproduce. The shortfall
  is 3, all in diversity, and its mechanism is visible in the same file (the code
  lift's 4 born facts = 1 language edge + the code halves of the 3 claims whose
  memory-side extraction never converged; 98 + 4 = 102 sources). Blending
  flattered the arm doing most of the growing. **Sizing now uses per-arm
  conversion and no blend**, to an expected **500** rather than to the 490 floor:
  377 claims (264 diversity + 113 `none`) ≈ **+603 captures**, 3.5× the corpus.
- **The 473 → 628 hazard is withdrawn.** `inverse_replacement` needs a live
  *inverse fact* in the same project with overlapping windows and a non-echo
  witness; a lone stray REPLACES edge arms nothing. Stronger: **k = 2 is
  unreachable in any corpus the committed loader admits** — wave 2 is refused
  outside the arming groups, so an accidental inverse pair lands whole in wave 1,
  is disputed ahead of the count, and never emits the `corroborated` event the
  audit's numerator joins on. Reaching k = 2 would take a weakened validator. The
  no-REPLACES rule is kept as hygiene; what genuinely threatens the count is
  supersession withholding a corroboration, which is a function of
  REPLACES-emitting captures × same-project in-window candidates rather than of
  density alone.
- **A third blocker was missed entirely and is the one that reshapes the route.**
  `fact_lift.CODE_FACT_PROJECT` is the constant `"default"` and `repositories`
  carries no project, so code-seconded `diversity` claims **cannot leave
  `default`** — a spread-authored one would hold at a single origin, refused by no
  validator. Multi-repo fixtures buy distinct dependencies, which §3.1 needs; they
  buy no project spread. So the monoculture concern lands in the arm the first
  sizing thought relieved it, and at the recommended split `default` holds **365
  of 510** promoting claims. That concentration is disclosure, not a defect to
  engineer away, and it travels with the eventual number.
- **The fixture fleet and the validator widening are both adjudicated** (Fable as
  escalation target, autonomous-loop §4; neither ruled owner-only). Ceiling: **six
  repos total**, new ones 40–90 imports each, a shared dependency core *required*
  (a pairwise-disjoint fleet is itself the manufactured signature), ≥10% of each
  repo's imports left unclaimed, role-coherent sets. The per-repo validator form is
  admissible on **intent** — `triple_key` embeds the subject and the code lift
  joins on canonicalised subject name per repo, so cross-repo seconding has no code
  path and claim-to-fact bijectivity survives — conditioned on five tests including
  a widening-delta pair test and enforced subject binding. The letter reading was
  priced rather than dismissed: it closes the diversity arm (the existing repo is
  claim-saturated) and forces ≈ +1092 captures, 1.9× the cost for no added
  independence.

**And the cost is not only effort, which is why it is recorded here rather than
in the task alone.** Every one of those captures is written by the measured
party, and the section above already names that as the audit's binding limit:
*a well-powered rule over authored evidence is a better instrument measuring the
same thing*. Clearing at ~500 makes the instrument decisive about a corpus its own
measurer wrote, and concentrating 264 of the new claims in one project to get the
near one-for-one conversion makes the denominator's authorship more visible, not
less. That is not an argument against the owner's instruction — the instruction
stands and `T2.131` executes it — it is the disclosure that has to travel with
the eventual number, so a future reader of "500 corroborations, bound 0.00945,
CLEARS" meets it beside what it was made of.

**No bar moved and none may.** The 0.01 bar and the 0.95 confidence are
untouched; this section changes a *target window*, which is a property of the
evidence, not of the gate.

### OWNER RULING on all three escalated items — 2026-08-13

Ruled the same day the run reported, on the run's own numbers and before any
further measurement. Recorded here because items 2 and 3 are
**gate-definition acts** and the evidence run was explicitly not entitled to
make them.

**Item 1 — what makes a zero-numerator audit measured: RULED — the corpus
grows past 100 corroborations AND the machine arm is armed.** Not the
alternative of ruling a dark numerator "measured with a caveat". The band
problem is the reason: at 20–99 corroborations one genuine dispute is
already ≥ 1 % and breaches the strict bar, so within that band a corpus is
either vacuous or failing, and the audit can only become *both* operable and
passable above 100. This ruling therefore does **not** move the 1 % bar —
which stands exactly where it was committed on 2026-08-07 — it moves the
census the bar is measured on. That direction is the point: the defect
attributes to the bar's interaction with small N, and the sanctioned repair
for that is a bigger N, never a looser bar (rule 3).

**Item 2 — may a route-(b) clear mint `promotion_metrics_record.json`:
RULED YES, with the caveat recorded.** A cleared bench run licenses the
mint, and the ledger row for that run must state in terms that production
badges are lighting on **corpus-design evidence** — probes 1–2 measure a
corpus authored to promote, which is evidence of mechanism and weak evidence
about organic behaviour (route (b)'s own stated caveat, unchanged). The
caveat lives in the ledger where the claim is made. **The mint remains the
owner's deliberate act on a cleared run and is never a side effect of
measuring**; nothing in this ruling licenses a harness to mint one.

**Item 3 — the arming path: RULED — the REPLACES-family corpus extension**,
which arms `inverse_replacement` deterministically and judge-free, so G-C's
machine-dispute arm acquires no dependency on G-D. The human arm
(`rejected_after`) stays dark by construction inside a harness run and is
not part of this path. Owning task: **T2.129**, minted below.

**What this does not do.** It does not clear G-C, does not mint a record,
and does not change any bar. `blocked ≡ 0` remains data-precluded until a
veto or a supersession-blocked hold actually fires in a measured window —
arming `inverse_replacement` is what makes that reachable, which is the
second reason item 3 was ruled this way rather than left to the human arm.

### G-C re-measure (2026-08-08, T2.111): **still NOT CLEARED**, and the audit was re-derived

Report: `docs/eval/2026-08-08-promotion-metrics.md`. Every probe reports the same
under-powered result as T2.40: 0 eligible transitions, 0 corroborations, 0 in
either audit arm, R2's fold companion 0. **The numbers did not move and the
verdict does not either.** What changed is what the numbers *mean*, and that is
the work this task existed to do.

**The audit's numerator arms, re-derived against T2.109's ratified shape.**
`_FALSE_PROMOTION_AUDIT_SQL` has exactly two arms: `disputed_after` (a `verified`
event whose `payload.after.verification_status = 'disputed'`) and
`rejected_after` (a `human_verdict` event with `verdict = 'rejected'`).

- The LLM `contradiction_scan` **no longer contributes to `disputed_after` at
  all.** Its finding now arrives on `contradiction_suspected`, which `decide`
  holds inert by construction — "no branch reads it, it appears in no
  condition, and every outcome this function can return is identical with it set
  and unset" — so it can produce no status transition and therefore no row this
  arm can see.
- `disputed_after` is consequently **judge-free**: its only remaining producer is
  the deterministic `adjudicate_contradiction_finding`, whose `inverse_replacement`
  arm needs a stored REPLACES-family edge and whose `single_valued` sibling is
  disarmed by an empty `SINGLE_VALUED_RELATIONS`.

**The G-C→G-D cross-edge, corrected.** The 2026-08-07 ruling — "G-C therefore has
G-D's judge qualification on its critical path", ratified into doc 20 §3 — was
true of the architecture it was written against and is **no longer true as
written**. The machine-dispute arm cannot be blocked by an unqualified judge
because the judge is not on it. The edge does not vanish, it lengthens and
changes kind: the scan's findings can still reach the audit, but only through
`rejected_after`, which requires a human to confirm a flag and reject the fact.
That route is gated on G-D passing **and** on a reviewer who can actually see the
suspicion.

**A cross-edge nobody had recorded: T2.112 sits on G-C's path.** A
contradiction-suspected fact currently reaches the review queue rendering
`unspecified`, with no counterpart and nothing to adjudicate against —
`review_queue._fact_reason` derives from the fact's own columns and the suspicion
is persisted in none of them. So today the human route is not merely gated, it is
**impassable**: even a qualified judge's findings could not reach `rejected_after`,
because no reviewer can confirm what they cannot see. T2.112 is therefore a
precondition for the audit's LLM-originated detection power, not a display
nicety.

> **Addendum 2026-08-09 — the route is passable now, and it took two landings.**
> T2.112 (`90b8fc7f`) persisted the flag as `contradiction_suspected_at` /
> `contradiction_counterpart_id` and served both from the queue — on the wire.
> The 2026-08-09 delta review found the screen still dropped them and the
> dismissal door had no caller at all, so the reviewer's only button *confirmed*
> the flag; `f0b2a2ed` renders the counterpart and ships the dismissal. The
> paragraph above is what a reader planning T2.40's re-measure needs corrected:
> "impassable" was true when written and again after the wire-only landing, and
> is false now. Note what the route still needs — a qualified judge (G-D, open)
> and a human who acts.

**The honest cost of the redesign, stated where it will be read.** G-D's
amendment bought veto precision by moving the scan off the veto. The same move
**reduces the audit's reach**: a detection route that was automatic
(scan → dispute → counted) is now human-gated (scan → review → human → reject →
counted). The audit's precision claim is unaffected; its *power* is strictly
lower, and the human-rejection arm's relative weight rises accordingly. Both
follow from one ratified decision and neither is a defect.

**The three vacuity clauses, ruled — they are cumulative and all three are now
answered.**

1. *The audit could read "decidable, clears" at 0.0000 with a structurally zero
   numerator.* **Vacuous for this run, live in principle.** Decidability requires
   ≥ 20 in-window corroborations (`false_promotion_min_corroborations`); there are
   0, so the audit cannot report decidable at all and the failure mode is
   unreachable. It stays live for any future run that reaches 20 corroborations
   while the numerator's producers remain dark — and note the reason a zero would
   be vacuous has *changed*: it is no longer "the judge is unqualified" but "the
   corpus carries no REPLACES-family edge and no human has adjudicated."
2. *Probes 1–2 read `slice_clears` True with `blocked ≡ 0` data-precluded.*
   **Vacuous for this run, live in principle.** With 0 eligible transitions both
   probes are under-powered and can neither clear nor fail, so the failing
   direction being unreachable costs nothing here.
3. *The substrate itself may be incomplete.* **OPERABLE AND UNRESOLVED — the one
   clause that is not vacuous.** Verified in code: `set_verification_status`
   ends with a bare `await record_event(...)`, no return inspected and no row
   counted back, and `record_event` degrades loudly but never raises into its
   caller. So a status UPDATE can commit while its journal row silently fails,
   and every G-C metric reads `events` alone — the loss lands in the
   **denominator**, which is the one direction that does not announce itself as
   under-power. The remedy pattern already exists in this tree: `dream_undo`
   counts its own `undone` rows back and raises when short ("an undo that could
   not be journalled does not happen"). Nothing applies it here. **This clause
   alone would prevent a future powered run from being trusted, and it has no
   owner.**

   > **Addendum 2026-08-09 — clause 3 has an owner, and is closed on both
   > streams.** T2.113 (`0d9b5dca`) was minted from this clause: `record_event`
   > now returns whether the row landed, and `set_verification_status` /
   > `ratify` raise `JournalWriteFailed` on a `False`, so a transition and its
   > journal row are atomic. The 2026-08-09 delta review then found the fix one
   > stream short — `record_human_verdict` and `dismiss_contradiction_suspicion`
   > still ignored the return — closed by `149f1f1e`. That half matters more to
   > *this* gate than the first: no column records a human rejection, so that
   > event row **is** the audit's `rejected_after` arm, and losing one deletes a
   > numerator rather than shrinking a denominator — the gate would read cleaner
   > than the system is. A powered run can now be trusted in both directions.

**No promotion record minted.** `app/services/promotion_metrics_record.json` stays
absent, so every promoted or born badge continues to serve as `candidate` with the
`verification_unmeasured` reason, scan-enforced.

### G-C verdict: **NOT CLEARED — the gate cannot yet be evaluated** (2026-08-07, T2.40)

**The measurement ran and the honest result is that no fact has ever flowed through the
counting ladder, anywhere this machine can see.** The production `darkmem` database is
migrated but its journal is empty (0 events of any type). The only corpus that exists —
the committed retrieval corpus, flowed end-to-end through the shipping lift and the
production recompute's fast drain (62 `sources_changed` events drained, 62 facts
recomputed, 0 live LLM calls, fingerprint `qwen3-embedding:0.6b|1024`) — is structurally
incapable of powering the gate: all 62 facts carry exactly one `fact_sources` row with a
NULL `origin_key`, which rule 4 of `fact_sources` folds into the reserved anonymous
bucket; that bucket counts once and is excluded from both gates by design, so no fact can
ever meet N on this corpus. A 0/0 is under-powered, not a pass, and it is recorded as
that. **The deriver lane's consequence holds where it now lives — on the label, not the
build** (M1 split, 2026-08-06): T2.27/T2.28 are merged, but
`claim_gates.PROMOTION_RECORD_PATH` remains absent — this run minted **no** promotion
record, so every born-`corroborated` row keeps serving as `candidate` with the
`verification_unmeasured` reason, scan-enforced. "The deriver lane stays closed" means
exactly that and nothing more.

**The reason this gate should not clear, looked for hardest and found (three, compounding):**

1. **Starvation is structural, not circumstantial.** No corpus with attributable,
   diverse origins exists; the bench corpus cannot be made to promote without authoring
   origin structure, and a corpus authored to promote measures its own design.
2. **The false-promotion audit's *broadest* systematic detector is dark until the
   `verification` judge qualifies.** The Tier-C LLM `contradiction_scan` reaches
   `VerificationJudge.judge()`, which refuses unconditionally without a qualification
   record (T2.41, behind T2.54's gold). **G-C therefore has G-D's
   judge qualification on its critical path** — a sequencing dependency stated nowhere
   before this run (T2.40's Depends list does not carry it), ratified into doc 20 §3 on
   2026-08-07. The dependency binds to G-D **passing at the currently configured judge
   identity**, not merely running: a G-D miss keeps this arm dark until a model or prompt
   change re-qualifies. Clearing G-C on a zero recorded while the audit's broadest
   detector was dark would certify the ladder's precision using an instrument that could
   not have caught most of an imprecision.

   **Second correction (2026-08-08, E2 whole-branch review, claim-honesty lens).** As
   first written *and as corrected on 2026-08-07*, this item said machine disputes "flow
   only through `contradiction_scan` → `VerificationJudge.judge()`". That is false, and
   the 2026-08-07 pass reinforced it rather than catching it. The veto has a **second,
   judge-free instrument**: `adjudicate_contradiction_finding` runs
   `CONTRADICTION_DETECTORS`, and `verification_ladder` reaches it on every recompute, so
   the `inverse_replacement` arm can dispute a fact with no qualification record. Whether
   it fires is a corpus property, not a code one — it needs a stored REPLACES-family edge,
   and T2.108's corpus had none, which is the finding that was mistaken for a code-level
   dead-end. The sibling `single_valued` arm is separately disarmed
   (`SINGLE_VALUED_RELATIONS` is empty). **G-C's verdict is unaffected** — the arm's
   sensitivity over a corpus with no such edges is nil, and the gate stays open on the
   corpus grounds of item 1. What changes is the *reason*: the judge is not a total
   barrier to machine disputes, and the gate-ordering analysis that ratified the
   G-C→G-D cross-edge never considered this arm. The cross-edge stands on the LLM scan's
   breadth; it does not stand on machine disputes being unreachable.

   **Correction (2026-08-07, Tier-3 analysis `2026-08-07-gate-ordering.md`, ratified).**
   This item originally read "human rejections flow only through a review queue that only
   disputes and blocked holds can fill. Both numerator arms dead-end today." **Both halves
   are contradicted by the shipped code, and the overstatement is corrected here so a
   future reader planning a fallback is not misled.** `human_adjudication.reject_fact`
   accepts *any* fact id — deliberately, since a corroborated fact has no opener firing on
   it and is therefore not on the queue at all — and journals a `human_verdict` event with
   `verdict='rejected'`, which is exactly what the audit's `rejected_after` CTE counts. No
   judge appears anywhere on that path. Nor is the queue's fill predicate judge-exclusive:
   `verification_ladder.REVIEW_OPENERS` also carries `_under_sourced_opens_review`, driven
   by source changes, never by the judge. So the human arm is **live**, and a zero from it
   is non-vacuous rather than dead — but its *sensitivity* is unknown and unmeasurable
   (nothing states what fraction of false promotions an unprompted human catches), so it
   cannot carry a "promotion precision ≥ 99%" claim on its own. The verdict below stands
   unchanged; only this supporting claim narrows from "both arms" to the machine arm.
3. **Once the record is minted, the badge outruns the measurement — say so here, where
   the number lives (T2.28's inherited consequence).** The promotion record this gate
   mints will light `corroborated` on born rows that the counting ladder never counted:
   they enter neither the promotion rate's numerator nor its denominator, never appear
   in the false-promotion audit, and their birth (and post-dispute restore,
   `_write_born_rung`) journals nothing, by design. Doc 10 §6's argument — *the parse is
   the verification* — may well be right, since a parsed import is not an inference. But
   G-C's number is a statement about the **counting** ladder only, and the badge it
   unlocks will also appear on rows outside that statement's scope. Any future reader of
   a cleared G-C row must read its claim that narrowly.

**What would evaluate this gate.** Either (a) a production journal window after the
homelab cutover, with organically captured facts asserted by ≥ 2 attributable
`origin_key`s across ≥ 2 source kinds or ≥ 7-day gaps, measured **after** T2.54 → T2.41
qualify the judge so the dispute arm is live — sized to at least one powered bucket per
axis (≥ 5 eligible), ≥ 20 distinct corroborated facts, ≥ 1 promote; or (b) a
purpose-built measurement corpus with designed origin/kind/time-gap structure, authored
under the gold discipline (separate owner, adversarial review — T2.54's pattern), with
the stated caveat that its promotion rate partially measures the corpus design, and the
same judge-qualification precondition for the audit. Hand-written journal rows evaluate
nothing and are forbidden in both branches.

**Twin (rule 2):** this run made **0 live LLM calls** (ingest fully cache-served; lift,
recompute and every metric are SQL); the bench arm end-to-end is ~40 s wall clock on the
dev machine, dominated by LAN embedding of the 94-entry corpus. There is no accuracy
figure here to twin — every rate came back undefined — but the cost column is recorded so
a future powered run has a baseline for what the measurement itself costs.

**Consequence of a miss:** the code-deriver lane (T2.27–T2.28) stays closed. The deriver
mints facts born `corroborated`; shipping it over an unproven ladder would put unverified
assertions into the vault at the ladder's second rung. *(Updated 2026-08-07: the lane's
code is merged under the M1 split; "closed" is enforced at the label —
`claim_gates.corroboration_gate` fails closed while the promotion record stays unminted,
and this run deliberately minted none.)*

---

## G-D — L2 → L3

**Owning task:** T2.41. **Bar lives in:** `config` + the gold set.

### The judge's prompt lost an undocumented suffix (2026-08-25) — measured inert

**What changed.** `_build_chat_body` appended a literal `" /no_think"` to the
last user message of every non-reasoning compat call. `verification` is
`reasoning=False` on an `openai` kind, so **every judge call carried it**,
including the sitting that minted the entailment record on 2026-08-17. It is a
qwen chat-template directive; OpenAI has never defined it. It is now opt-in per
purpose (`prompt_no_think`) and no purpose sets it, so the judge no longer
receives it.

**Why this needed measuring rather than asserting.** `judge_identity` hashes
`SYSTEM_PROMPT + "\x00" + USER_TEMPLATE` — the *template*, not the message that
is sent. The suffix was applied downstream of that hash, so removing it changes
the judge's input **without moving `fd39e7b2c47fa375`**. That is precisely the
shape doc 17 §6 guards against: a qualification that silently stops describing
the thing it qualified.

**Measurement.** 30 gold pairs (deterministic stride over `gold.json`), judge
`gpt-5.5` at `reasoning_effort: high`, three arms per pair — without the suffix,
without it *again* as a control, and with it.

| Arm | Verdict disagreements / 30 |
|---|---|
| control (identical prompt, sent twice) | **2** |
| suffix vs no suffix | **1** |

Agreement with gold was 22/30 without and 23/30 with. **The suffix's effect is
smaller than the judge's own run-to-run noise**, and the single pair that moved
(`eg-0698`) is one the control arm also moved, so it is unstable rather than
suffix-sensitive. The record continues to describe the running judge, and the
change moves the sent prompt *toward* the template the identity hashes rather
than away from it.

**The control arm is a finding in its own right, and it is not a comfortable
one.** `gpt-5.5` at high effort is **not deterministic**: 2 of 30 verdicts
flipped on a byte-identical request with a fixed `seed` — OpenAI's seed is
best-effort, not a guarantee. Every number in the entailment record
(precision 0.9906, recall 0.9545) comes from a **single sitting** of that judge,
so each carries an unquantified re-run variance that no artifact currently
states. Nothing here re-opens the mint; it records that the figures are one
draw, not a constant, and that a re-run landing slightly differently would be
the instrument, not a regression.


| Probe | Bar | Measured | Artifact | Verdict |
|---|---|---|---|---|
| `verification` judge precision on labelled entailment gold | ≥ 0.95 on `entailed` (`groundedness_gate_precision_bar`, config default; stated 2026-07-31, before any gate run) | **0.9895** (deepseek) / **0.9806** (gpt-5.5) | `docs/eval/2026-08-08-judge-qualification-4d886440.md`, `-1bb9d9ba.md` | **PASS** both |
| `verification` judge recall on labelled entailment gold | ≥ 0.90 on `entailed` (`groundedness_gate_recall_bar`, config default; stated 2026-07-31, before any gate run) | **0.9307** (deepseek) / **1.0000** (gpt-5.5) | same | **PASS** both |
| `verification` judge precision on the **contradiction** verdict | ≥ 0.95 (`contradiction_precision_bar`, config default; stated 2026-07-31) | **0.7937** (deepseek) / **0.8814** (gpt-5.5) | same | **FAIL** both |

The veto consumer inherits the same qualification on the **contradiction** verdict
(doc 17 §6): `contradiction_precision_bar` = **≥ 0.95**, config default, stated
2026-07-31 before any gate run alongside the two above.

### G-D re-measure under the redesign (2026-08-08): **NOT CLEARED — one bar, one slice**

The first measurement of the redesigned gate, on the grown gold after its
Layer-3 ruling and certification. Report:
`docs/eval/2026-08-08-judge-qualification-fd39e7b2.md`.

| Bar | Value | Pooled (351) | Never-contacted (110) |
|---|---|---|---|
| `groundedness_gate_precision_bar` | 0.95 | 0.9932 **PASS** | 1.0000 **PASS** |
| `groundedness_gate_recall_bar` | 0.90 | 0.9932 **PASS** | 0.9778 **PASS** |
| `contradiction_precision_bar` | 0.70 | 0.9012 **PASS** | 0.9200 **PASS** |
| `contradiction_recall_bar` | 0.95 | **0.9125 FAIL** | **0.9200 FAIL** |

> **Provenance note added 2026-08-09 (delta review D-6): this run's
> never-contacted column is ledger-only.** The subset renderer landed in
> `47e3dce1`, the same commit that recorded the run, and the run's own recorded
> sha (`e69895cb`) predates it, so the committed report carries no subset
> section and the entailment cache the cells derive from is untracked. Three
> checks were run against that: the four cells are arithmetically consistent
> with the report's pooled confusion, the run ledger holds exactly **one**
> attempt row for gold sha `800d4d91` (so "no extra gold contact" survives its
> own counting rule, warm replays included), and the verdict does not turn on
> the column — the gate fails on pooled recall either way. Forward-closed: the
> runner now renders the subset, so the next run's column comes from its own
> report.

**The redesign's own prediction held, and that is the first thing to say.**
Precision — repriced from truth to review-load — came in at 0.90 against the
0.70 floor, comfortably. The gate now fails on the metric the amendment made
truth-critical, which is the gate working as redesigned rather than failing in
a new place. Recall 0.9125 = 73/80; the bar needs 76/80. **Three pairs.**

**The failure is one rule, not a diffuse weakness.** All **7** contradiction-recall
misses are `value-swap`, every one judged `unsupported` — the slice whose
verdict is fixed by the exclusive-slot rule. The judge is declining to treat a
differing value in a single-valued slot as *exclusion*, falling back to
"contradiction requires exclusion, not absence". The precision errors sit
elsewhere entirely (6 `temporal`, 2 `direction`), so the two metrics are failing
on disjoint material.

**Two checks that close off the easy explanations, both pre-existing rather
than constructed after the number:**

1. *Is the gold wrong?* No, and this is the strongest evidence available. The
   n = 93 Layer-3 resample draws a **full census of the contradicted class**, so
   every one of the 42 `value-swap` pairs was independently re-labelled blind by
   a non-Claude model days before this run. It returned **one** disagreement in
   93, and that one was `temporal` (eg-0018), not `value-swap`. The six host-swap
   pairs this file had flagged as "procedurally weak evidence... exactly the pairs
   the resample's full contradicted census exists to test" were tested, and held.
2. *Is the prompt missing the rule?* No. `SYSTEM_PROMPT` lists under
   `contradicted`: "a different value in a slot the premise fills exclusively".
   The judge was told the rule and did not apply it. So this is not a
   prompt-coverage gap, and editing the prompt would be tuning against the set
   that measured the failure — barred by doc 17 §6 and unnecessary on the facts.

**Rule B was enforced for the first time here, and it was not previously
implemented.** LABELLING.md's contacted-pairs rule requires every barred metric
on both populations "with the gate verdict required to hold on both"; the runner
scored the pool only. It now scores both from the verdicts already in hand — no
extra model call, no extra gold contact. The subset agrees with the pool on every
bar, including the miss, so pooling was not hiding anything **this time**. Note
the 241 pairs below the boundary had been contacted three times, which is exactly
the blend the rule exists to prevent being read as one number.

**A granularity finding the subset exposes, recorded because it will matter
before it bites.** The never-contacted subset holds 25 contradicted pairs, so its
recall lattice is 1.00 / 0.96 / 0.92 — **0.95 is not on it**, and the subset
therefore enforces ≥ 0.96 (at most one miss in 25) where the pooled census
permits four in 80. T2.110 sized the pooled census at 80 precisely so 76/80 lands
on 0.9500 exactly; that analysis was never run for the subset Rule B also gates.
**It is not load-bearing for this verdict** — the subset scored 23/25, which
fails against 0.95 and 0.96 alike — but a future run landing on 24/25 would be
passed by the stated bar and failed by the lattice, and the owner should settle
whether the subset gates or is reported-only before that happens.

**Attempts and provenance, stated plainly.** `gold_touching_attempts` keys on
`gold_sha256`, so this is attempt **1** on the grown gold; doc 17 §6's two-attempt
budget has one left. The judge identity is `fd39e7b2c47fa375`
(`gpt-5.5`, `params={"reasoning_effort":"high"}`), which is **not** attempt 2's
`1bb9d9bae62eb9d8` even though the model and the prompt are the same — `params`
is in `IDENTITY_FIELDS`, and attempt 2's params are unrecoverable (the resolution
spike probed ~18k candidate configs and had to fall back to token-checksum
attribution; an independent search here also found nothing). The prompt is
byte-identical across both: `prompt_sha f99151e4add69b31`. Because the cache key
folds in the identity, **nothing replayed warm** — all 351 pairs are fresh
inference. Reports since 2026-08-08 record the full invocation, so this gap is
closed forward and cannot be closed backward.

**Deliberately not recorded here: the per-pair miss census.** Publishing the last
one is part of what contaminated the 241-pair gold and forced T2.110's growth
round. The slice-level attribution above is what a decision needs; the pair ids
are what a future author must not be able to read.

**No qualification record was minted**, and `verification_qualification.json`
does not exist. G-D stays closed and the judge stays unqualified, so
`VerificationJudge.judge()` still refuses and the Tier-C scan still produces
nothing.

### G-D — the Rule B census resize (T2.115, rulings 2026-08-10)

Not a gate run. The 2026-08-08 re-measure recorded a granularity finding and
asked the owner to settle it before a run landed on it; this is that settlement
and the round it authorises. **G-D is unaffected — it stays open, and no
attempt is spent here.**

**The finding.** Rule B's second population holds **25** contradicted pairs, so
its recall lattice is 1.00 / 0.96 / 0.92 — **0.95 is not on it** — and "the gate
verdict required to hold on both" therefore makes it enforce ≥ 0.96 where the
pooled census permits four misses in 80. It did not bite the last run (23/25
fails against 0.95 and 0.96 alike); a run landing on 24/25 would be passed by the
stated bar and failed by the lattice.

**Four rulings, 2026-08-10.** Ratified by the owner as an instruction to proceed
on the text as drafted and Fable-reviewed; the drafting is the agent's, the
adoption is the owner's, and that distinction is recorded rather than dressed up
as owner-authored reasoning.

| # | Ruling | Why it was the owner's |
|---|---|---|
| R1 | Resize so 0.95 lands on the second population's lattice, then let it gate | changes what the gate means |
| R2 | Route: retire-and-replace at a **constant pooled census** — contacted contradicted 55 → 40, second population 25 → 40, pooled held at 80 | the only route changing nothing already ratified |
| R3 | Rule B's second population is **redefined and renamed**, not abolished; the boundary constant stays `eg-0242` | weakens ratified protocol text |
| R4 | The sha-keyed attempt budget is **reported by lineage, not blocked** | gate integrity |

**Two derivations bound R2, and both were independently re-derived in review.**
0.95 sits on a recall lattice only at `n ≡ 0 (mod 20)`; for **growth-only**
routes pooled is `55 + N`, so both populations exact needs `N ≡ 0` and
`N ≡ 5` — no solution. And the census cannot simply grow: the Layer-3
resample's first stratum is a **full census** of `contradicted` at a ratified
`n = 93`, enforced in code (`resample_draw.draw` raises above `RESAMPLE_N`).
Retirement is what dissolves the first contradiction, by moving the 55.

**R3, stated plainly because it is a weakening.** The 2026-08-08 re-measure ran
fresh inference on **all 351 pairs** ("nothing replayed warm"), so a literal
never-contacted population has not existed since. The strict reading is
unsustainable besides — every run scores all live pairs, so the population would
empty after every attempt. The population is now *pairs not contacted before the
grown-gold attempt, with the per-pair miss census withheld*, and the withholding
is what keeps it meaningful: one contact without published feedback is
materially unlike the 241 pairs' three contacts with a public failure census.

**R4 — the budget lineage, recorded here first so no later run can be the first
to mention it.** `gold_touching_attempts` keys on `gold_sha256`, so any census
reshape mints a fresh two-attempt budget as a side effect. Unguarded that is a
loophole: a failed gate could be followed by a reshape that resets its budget.
The owner ruled visibility over prohibition, matching how this corpus already
treats gold contact. **Lineage at the time of writing: gold `800d4d91` — 1
attempt (`fd39e7b2`, 2026-08-08); ancestor `047cbd6f`/pre-growth — 3 attempts
across two judge identities. The resized gold starts at 0 on its own sha and
inherits a recorded lineage of 4.**

**The round is blocked on nothing measurable and everything procedural.** Its
step-level plan (`docs/superpowers/plans/2026-08-10-entailment-gold-subset-resize.md`)
was reviewed at Fable tier and returned *not safe to execute as written* with two
Criticals — a boundary constant that would have shrunk the gated population to 15
contradicted pairs, and a stale `resample` block that would have read
`gate_eligible = True` through the whole round on a certification of a different
file. Both are fixed in v2. The authoring is firewalled from every G-D artifact
including the untracked per-pair verdict cache, because the controller running
the round has read the slice-level failure attribution and cannot author.

### Adjudication of C-1, C-2, T2.114 and the doc 09 §4.1 deviation (2026-08-10)

**How these were decided, stated first because it is the part that can be
wrong.** The owner delegated the open blockers to the assistant ("resolve all
blockers yourself"). That transferred **authority** and not **information
state**: this session had already read the slice-level failure attribution and
both measured judges' results, so doc 17 §6's fitting rule still bound it
wherever a decision could be selected for its effect on a measured outcome. The
drafts were therefore written to be content-blind and **then attacked by a
Fable-tier reviewer before any of them landed**. The reviewer refused one
outright and found a false claim in another; both refusals are recorded below,
because a ruling that survived review reads the same as one that was never
reviewed unless the failures are kept.

**R-A — C-1: amend clause 5 forward; the round is not absolved.** Ruled option
(a). Clause 5 gains 5a/5b/5c in LABELLING.md. Two things happened in the round
and only one is a defect: blind authoring returning an `overreach`-contradicted
pair where the slot targeted `temporal` is a content fact nobody may overrule,
while sizing the temporal batch at 2 *afterwards, to hold the census at 80*,
was an informed party choosing which slice absorbed a shortfall in a gated
census, recorded nowhere. 5a routes the first case to the skip-and-re-author
mechanism the protocol already has (the first draft forbade re-authoring
outright, which the reviewer showed was **incoherent** — a *verdict* deviation
leaves the census short and no absorption rule restores it without
re-authoring). 5b requires the absorbing rule to be committed code before
authoring, as clause 3 already requires of the draw, because "largest
remainder" alone leaves the reference distribution and population unstated and
a contaminated controller would pick the reading. 5c states that the amendment
binds the next round and absolves this one: amending a rule so a completed run
becomes compliant is the same move as moving a bar so a run passes.

*Disposition: the census stands, no gold surgery.* Grounds are the cost (any
repair moves the sha, voids the `58ac1a90` certification and the spent attempt)
and that the selection would be made by a contaminated party. **The draft's
third ground — "the run did not clear, so the deviation cannot have
manufactured a pass" — was struck as unsound**: the deviation lives in the
*gold*, not the run, so it is inherited by every future measurement on this sha,
which the disclosure paragraph itself concedes.

**R-B — C-2: rule the rule, build the check, and gate the ordering.**
Independence is ratified as a property of the **proposition, not the bytes**,
and ships as `scripts/benchlib/duplicate_propositions.py` rather than as a
second prose instruction — the finding was precisely that an instruction aimed
at two visible collisions could not reach the one that never collided.

*The check immediately paid for itself twice.* Written naively it missed **both**
duplicates it was built for, because the tokenizer let a sentence-final period
ride along (`partition.` ≠ `partition`); and once fixed it reported 19 pairs,
most of them a reversal beside its non-reversal, because discarding word order
conflates "same proposition" with "same entities mentioned". Scoped to a shared
premise **and verdict**, with light suffix folding so `replaces`/`replaced` meet,
it reports **nine** duplicate relations — against the two the branch review found
by eye. Two are `contradicted` and inside the gated census; seven are `entailed`.

*The correction that matters most.* The draft claimed the duplicates bias the
gate **strictly** — "cannot have made it easier". That is false and false in the
reassuring direction. A judge that *misses* a duplicated proposition burns two
of four permitted misses; one that *catches* it banks two correlated hits and may
then miss four of the remaining 78 independent items, a per-item tolerance of
4/78 ≈ 5.13% against the intended 4/80 = 5.00%. At measured recall ≈ 0.94 the
catch is the common case, so the common case is the **easing** one. The live
instance is sharp: attempt 1 scored Rule B at exactly **38/40 = 0.9500**, a
zero-margin pass whose independent-item reading falls below the bar. And the
pooled contradicted census carries **78** independent propositions, not 79 — the
draft, and the C-2 entry below, both undercounted by one because `eg-0251` also
sits in Rule B's population, so **both** duplicated propositions straddle.

*Therefore an ordering gate, not just a record:* **no further judge attempt may
run on gold `98fc4b49` until the two contradicted duplicates are retired and the
gold re-certified.** Spending the final sanctioned attempt against a census with
a known bar-easing correlated duplicate, and repairing afterwards, is the one
ordering that could manufacture an edge pass out of a defect already on the
record. Retiring them is content-forced by a deterministic finding rather than a
census-shape selection, so clause 1 does not govern it and contamination is not
the obstacle.

> **SUPERSEDED 2026-08-12 by owner ruling — independence is handled by
> reporting, not by retiring. The ordering gate is lifted.**
>
> Recorded as the owner's. The census keeps its 80 rows, the two duplicated
> propositions stay live, and every qualification run now discloses that the
> class carries **78 independent propositions** and names the duplicates
> (`eg-0093`+`eg-0367`, `eg-0194`+`eg-0251`).
>
> **What forced the re-ruling.** Executing R-B as written was found on
> 2026-08-12 to be impossible without moving a ratified bar: retiring two rows
> takes the pooled contradicted census to 78, where the minimum passing score
> becomes 75/78 = **0.9615**, and Rule B's to 38, where it becomes 37/38 =
> **0.9737**. Since the verdict must hold on both, the binding bar would have
> risen to 0.9737 — 2.37 points above the ratified 0.95, by arithmetic and
> nobody's argument. That is the defect T2.115 was minted to fix, reintroduced
> more severely by the ruling meant to fix a different one. No retirement
> avoids it: any two-row reduction breaks the lattice, and retiring one from
> each population lands on 39 (0.9487, also inexact). Analysis:
> `analyses/2026-08-12-gd-decision-state.md`.
>
> **What this ruling costs, stated where the number lives.** The bar is still
> applied to rows, so a run scoring exactly 76/80 passes at the stated 0.95
> while its independent reading is 74/78 = 0.9487 — below the bar — if the
> judge caught both correlated pairs. **A zero-margin pass is therefore not
> robust to the independence reading, and a run that lands on one must say so
> rather than be read as a clear pass.** The run report now computes and states
> exactly this. The easing R-B objected to is real and is accepted with its
> eyes open; what changes is that it can no longer be invisible.
>
> **What it buys.** No gold surgery, so `58ac1a90` stands, no fresh n = 93
> sitting is owed, and the one remaining sanctioned attempt is not spent
> repairing a census. T2.114 is no longer gated behind R-B and is blocked on
> R-C alone.

**R-C — T2.114: NOT RULED. The one blocker the delegation could not dissolve.**
The draft argued that no selection existed to make, because attempt 1 on this
gold used `deepseek-v4-flash` and only one other model carries a qualification
record, so "a different judge model" had exactly one referent and a choice among
one option cannot be a fit. **The reviewer refuted it and the refutation is
accepted.** The eligibility filter — *"already carries a qualification record"* —
appears nowhere in T2.114 or doc 17 §6; this session invented it, and it is
exactly what shrinks the referent set to one. `deepseek-v4-pro` is a reachable,
credentialed, different model. There are real arguments against it (it sat the
Layer-3 resample, so judge and certifier would be one model) — but making them
is performing the judgment the draft claimed did not exist, and performing it
while knowing which judge scored better. A reader who knew nothing could not
distinguish the result from score-chasing. Terminology gave the strain away too:
the draft wrote "already-qualified judge" when **no judge has ever qualified** —
both carry *failed* records.

So T2.114 stays `blocked`, and the reason is information state rather than
authority: the argument's whole evidential value is that it was made by someone
who had not seen the scoreboard. The three sentences it needs are unchanged —
which model, why that one, and what result ends the search rather than extends
it — and the option set is now known to be at least {`gpt-5.5`,
`deepseek-v4-pro`}, with v4-pro carrying the resample-circularity objection
above. ~~**Note this is now also gated behind R-B: whichever model is chosen, no
attempt may run on `98fc4b49` until the duplicates are retired.**~~
**Struck 2026-08-12: R-B's ordering gate was lifted by the owner ruling above.**

> **R-C WAS SATISFIED THE SAME DAY, and this entry never said so.** This
> adjudication landed at 18:59 on 2026-08-10 (`120e32a2`); the owner supplied
> the ruling at 19:14, fifteen minutes later (`948a1a2d`), and it is recorded
> in `tasks/M1-measurement.md`: **the model is `gpt-5.5`**, with the binding
> stopping rule — final attempt on this gold, a miss records NOT CLEARED and no
> further model is tried on that sha. **Re-affirmed by the owner 2026-08-12.**
>
> Two of R-C's three sentences are therefore on the record and the third is
> deliberately absent: the ruling states that no session may "embellish it into
> a rationale", so the *why* is the owner's and is unrecorded by design rather
> than outstanding. An owner may choose without justifying the choice to their
> own tooling; what the corpus forbids is an assistant manufacturing the reason
> afterwards.
>
> **Consequence for anyone reading this entry alone:** T2.114 has not been
> blocked on R-C since 2026-08-10. What actually held it after that was R-B's
> ordering gate, lifted above. With both closed the task is **startable**, and
> its own text binds who may run it — not the session that authored the
> surrounding work.

**R-D — doc 09 §4.1: adopt the damping (Tier-3, ratified).** `ln(1+x)` per
signal is now the stated formula. `review_ranking` already compresses
identically; the undamped form defeats its own rationale, since a 400-neighbour
hub out-scores the weights by arithmetic rather than intent; and nothing
measured is fitted, because the weights are untuned and T3.02 sits behind G-D —
a curve chosen before data, which is the only honest time. The curve is part of
what a future weight-tune is measured *against*, so a retune moves `w_*` and
never the damping.

### T2.115 — two defects found by the branch review, awaiting owner adjudication

Found 2026-08-10 by the whole-branch review, after the round had been committed
and after the G-D attempt above had run. **Both are in the round's execution and
both were verified at the file before being recorded here.** Neither is a
measurement error; both are claims the artifact does not support, which is this
corpus's characteristic defect appearing in the round that was most careful
about it.

**C-1 — the round violated the clause it ratified, and three in-tree sentences
say otherwise.** Clause 5 of the lattice-retirement rule requires the affected
verdict class's "largest-remainder slice distribution ... unchanged after
replacement". Measured: retired `value-swap` 8 / `direction` 4 / `temporal` 3;
replaced `value-swap` 8 / `direction` 4 / `temporal` **2** + `overreach` **1**.
Pooled contradicted moved `temporal` 15→14 and `overreach` 0→1.

What actually happened, stated plainly because it is worse than an oversight:
authoring returned one `overreach`-contradicted pair (a lawful but rare shape the
author flagged at the time), and the temporal batch was then sized at 2
contradicted instead of 3 **to keep the census at 80** — the verdict arithmetic
was rebalanced around it and the composition deviation was recorded nowhere.
Contradicted by commit `48ad7e8e` ("composition preserved"),
`entailment_assignment.py` ("unchanged end to end (rule clause 5)") and its
round-3 comment ("3 contradicted + 3 entailed + 3 unsupported", shipped 2/3/4).

**The rule as written cannot fix its own violation.** The obvious repair —
retire the `overreach`-contradicted pair and author a `temporal` one — is barred:
`eg-0405` is in Rule B's population and clause 1 admits only *contacted* pairs.
So the owner's options are to amend clause 5 (e.g. permit a recorded deviation
with its arithmetic), to relax clause 1 for this repair, or to accept and record
the deviation as standing. **An agent may not pick among these**: clause 5 is
ratified text and the choice changes what a future round may do.

**C-2 — a semantic near-duplicate entered the census through the loophole the
round itself documented.** Three anchored `direction` slots sat on facts already
carrying a live `direction` pair. Two produced byte-identical hypotheses, were
caught by the loader's uniqueness check, and were skipped with the instruction —
recorded in History — **"do not resolve it by rewording"**. The third never
collided byte-for-byte: `eg-0367`'s hypothesis says the same thing as
`eg-0093`'s in different words, so it passed. The instruction was given for the
two collisions that were visible and could not reach the one that was not.

Consequence: the pooled contradicted census is 80 rows and at most 79
independent items, and Rule B's 40 contains one proposition the contacted
population already held. The honest reading of the G-D entry above must carry
this, and it now does.

**Deliberately not fixed by this session.** Every repair is gold surgery, which
moves the sha, voids the `58ac1a90` certification and the attempt just spent, and
re-opens a census the owner ruled on. The findings are recorded where the next
reader meets them; the ruling is the owner's.

> **Adjudicated 2026-08-10 — see "Adjudication of C-1, C-2, T2.114 and the doc
> 09 §4.1 deviation" above.** C-1: clause 5 amended forward (5a/5b/5c), the
> round not absolved, the census left in place. C-2: independence ratified at
> the proposition and enforced by a committed check, which found **nine**
> duplicate relations rather than two. **Two corrections to the text above:**
> the contradicted census carries **78** independent propositions, not 79 —
> `eg-0251` is also in Rule B's population, so *both* duplicated propositions
> straddle, not one — and no further judge attempt may run on `98fc4b49` until
> the two are retired and the gold re-certified.

### G-D re-measure on the resized gold (2026-08-10, T2.115 follow-on): **NOT CLEARED — pooled recall, by one pair**

Attempt **1 of 2** on gold `98fc4b49` (lineage: 4 prior attempts across two
ancestor golds, per ruling R4). Run from a **fresh session** — the controller
that resized the gold authored its pairs and did not measure them. Report:
`docs/eval/2026-08-10-judge-qualification-4d886440.md`.

| Bar | Required | Pooled (402) | Rule B population (176) |
|---|---|---|---|
| `groundedness_gate_precision_bar` | 0.95 | 0.9938 **PASS** | 1.0000 **PASS** |
| `groundedness_gate_recall_bar` | 0.90 | 0.9249 **PASS** | 0.9167 **PASS** |
| `contradiction_precision_bar` | 0.70 | 0.8065 **PASS** | 0.8837 **PASS** |
| `contradiction_recall_bar` | 0.95 | **0.9375 FAIL** | **0.9500 PASS** |

**Verdict: NOT CLEARED.** Rule B requires the verdict to hold on both
populations. Pooled contradiction-recall is 75/80 — five misses where the bar
permits four. Seven of eight bar readings pass.

**The resize put 0.95 on the subset's lattice, and Rule B's population scored
38/40 = 0.9500 exactly.** Before the round, 25 contradicted pairs offered only
0.92 and 0.96, so this same judge performance would have been measured against a
bar its census could not express. That much holds.

> **Correction, same day, from the branch review (C-1/C-2).** The paragraph
> above originally read "the resize did the thing it was built to do, and this
> run is the demonstration". **That claim is stronger than the artifact
> supports and is withdrawn**, for two reasons found after this entry was
> written and both confirmed at the file:
>
> 1. **The census is 80 rows and fewer than 80 independent items.** New
>    `eg-0367` and live `eg-0093` share an identical premise
>    (`hv-27 has part scratch partition`) and semantically identical reversal
>    hypotheses, both `contradicted`. The lattice-exactness argument presumes 80
>    independent trials. Worse for *this* run: eg-0367 is in Rule B's population
>    and eg-0093 is in the contacted one, so the judge had already met that
>    proposition — the subset's "not contacted before" property is dented in
>    substance for one of the 40 pairs whose exactness the paragraph celebrates.
> 2. **The retirement's slice composition was not preserved.** Retired
>    8 value-swap / 4 direction / 3 temporal; replaced 8 / 4 / **2** plus one
>    **overreach**-contradicted. The pooled contradicted distribution moved
>    (temporal 15→14, overreach 0→1), which ratified clause 5 forbids.
>
> Neither changes a measured number and neither is a reason to re-run: the bars
> read what they read. What changes is what may be *claimed* from them. Both are
> owner-adjudication items below.

**This is a different judge from 2026-08-08, and the comparison is not clean.**
The judge here is `4d886440` (`deepseek-v4-flash`), the configured `verification`
purpose on this machine; 2026-08-08 ran `fd39e7b2` (`gpt-5.5`), which is not
reachable from here. So pooled 0.9375 against that run's 0.9125 crosses **both**
a judge change and a census change, and — per the section below — the
retirement's overlap with that run's misses is unattributable. **The delta is
not evidence of a better judge and is not recorded as one.**

**What the per-pair artifact bought immediately.** The five pooled misses are
3 in the contacted population and 2 in Rule B's, by slice `temporal` 2,
`direction` 2, `value-swap` 1. Contrast 2026-08-08, whose seven misses were
**all** `value-swap` — a different judge failing differently, which is the sort
of claim that could not be made before today because no artifact joined a pair
id to a verdict. Future comparisons *against this run* are attributable; every
comparison across it and 2026-08-08 is not.

**Nothing was tuned and nothing re-run.** One attempt, one report, the number
recorded as it landed. The remaining lawful moves are unchanged and are the
owner's: the second attempt at a frozen prompt with a different judge model, or
a recorded argument about the bar. Note the fitting rule still binds — the
per-pair census above may not be used to author or retire pairs.

#### The overlap disclosure T2.115 owed, and could not compute

The plan review (I6) required the round's report to state **how many of the 15
retired pairs were misses in the last recorded attempt** — otherwise a future
re-measure's recall moves for census-content reasons and nobody can tell that
from a judge change. It judged the number "computable by the
already-contaminated controller" from the quarantined per-pair verdict cache.

**It is not computable, and the reason is a gap worth more than the number
was.** Three routes, all closed:

1. **Exact join.** The cache is keyed on
   `sha256(purpose, purpose_identity, messages, kwargs)`, and
   `_KEYED_CONFIG_FIELDS` folds in `base_url`, `api_kind` and `params`. The
   2026-08-08 attempt's `base_url` is recorded nowhere; 24 candidate configs
   reproduced zero keys. This is the same wall this file already records for
   attempt 2's params, where a ~18k-candidate search failed and fell back to
   token-checksum attribution.
2. **The run report.** `docs/eval/2026-08-08-judge-qualification-fd39e7b2.md`
   carries the confusion matrix and per-slice accuracy and **no per-pair
   census** — withheld deliberately, as this file states, because "the pair ids
   are what a future author must not be able to read".
3. **Text attribution.** Matching cached reasons to pairs by distinctive tokens
   collides across pairs — `wireguard`+`deployed` matches two retired pairs and
   pools their responses across every attempt — so the counts blend pairs and
   sittings. A number from this would look like evidence and be noise.

**The tension is real and is the point.** The per-pair census is withheld so a
later author cannot aim at it; that same withholding makes the retirement's
effect on the next re-measure unattributable. Both properties are wanted and
the current artifacts cannot have both.

**Forward fix, for whoever runs the next qualification.** The run should emit a
`{pair_id: verdict}` artifact beside its raw cache, in the *same* contaminated
category — quarantined from every authoring allowlist exactly as
`entailment/cache/` now is, never published in the report or this file. That
gives a controller the join without giving an author the census. Until it
exists, **a re-measure on the resized gold cannot separate a census-content
delta from a judge delta**, and any comparison against the 0.9125 recorded on
2026-08-08 must say so.

### G-D ruling (2026-08-12): **R1 ratified as a design correction. The composed mint is REFUSED. The entailment role qualifies on a fresh gold or not at all.**

The owner's holdings on the two questions v0.5 put, taken after an independent Fable-tier
review that sat outside the authoring lineage of the proposal it judged.

**Q3 — is R1 a distinct structural move, or a third attempt in disguise? RULED: a
structural move, and ratified as a standing Tier-3 correction to doc 17 §6 and doc 20 §4.**
The distinction that carries it, in the reviewer's formulation rather than the proposal's:
in both post-failure re-cuts of G-D — the 2026-08-08 redesign after the precision failures,
and R1 after the recall failure — **the failed bar never moved and the failed capability
never became qualified.** Re-cutting *to pass* unlocks what the failed bar protected;
re-cutting *to scope* does not. `contradiction_recall_bar` stays 0.95, the contradiction
role stays NOT CLEARED, the Tier-C scan stays dead, and the stopping rule's two moves
remain its only futures.

Ground 3 as the proposal wrote it — "no selection was possible, the entailment pair never
failed" — is true on the numbers and answers the wrong level. Selection operated on *when
the split was proposed*: had the contradiction pair passed on 2026-08-12, R1 would not
exist. The ratification is made in the knowledge of that, which is what makes it a holding
rather than an inference.

**An expiry check rides with the ratification.** If the contradiction role is never
re-attempted on either of the stopping rule's sanctioned moves within roughly two quarters
of this entry, the split reads retroactively as burial rather than separation. That
outcome is to be recorded here as a finding about this ruling, not quietly tolerated.

**Q4 — is the composed outcome intended, where the run recorded NOT CLEARED becomes the
run whose verdicts mint the redefined gate's record? RULED: NO. The composition is
refused.** R2's offline re-score is **deferred, not adopted**, and the entailment role's
record will be minted from a **fresh gold** or not at all.

Three reasons, and the first is the one that decides it:

1. **Deferring costs approximately zero calendar time.** The entailment record opens the
   L3 path, but articles synthesise only from corroborated or confirmed facts, and
   production can produce none until a real corpus exists — measured this day at 2
   memories, **zero attributable origins** (its single `unknown:api:default` key folds into
   the reserved anonymous bucket), 1 `candidate` fact, 0 articles. The critical path runs
   through capture either way, so the mint buys nothing it would not have anyway.
2. **A fresh sitting on this gold is not merely barred but meaningless.** The stopping rule
   binds contacts with pair set `4975c5cc`, and the frozen judge identity would be served
   warm cache verdicts byte-for-byte — the T2.114 run was itself 338/402 replays of the
   2026-08-08 sitting. Only a new gold can produce an independent number.
3. **A new gold is owed regardless, on grounds that cite no result.** This gold's
   false-positive censuses are published in this file, so it is **publication-contaminated
   for all future qualification**; and T2.118 found the entailed class was never
   lattice-sized to its own bar and carries five duplicated propositions over one
   three-wide component.

The standing rule this sets: **a record that needs a paragraph explaining why the NOT
CLEARED run minted it is a record this project does not want.** A fresh-gold record needs
no such paragraph.

**What this ruling does not do.** It does not clear G-D on either role. It moves no bar.
It leaves the stopping rule intact and unbreached — `4975c5cc` is retired from
qualification use, and any future run against those pairs must refuse for **any** role.

### G-D final attempt (2026-08-12, T2.114): **NOT CLEARED — contradiction recall, both populations. The stopping rule has fired.**

Attempt **2 of 2** on pair set `4975c5cc` — the counter keys on the pairs since
T2.116's ruling, and it read **1** (deepseek-v4-flash's 2026-08-10 contact)
before this run. The file sha is `6eadba73`, moved from `98fc4b49` by T2.116's
certification stamp; the pairs did not move. Run under the owner's ruling
(2026-08-10, re-affirmed 2026-08-12): **the model is `gpt-5.5`**, chosen by the
party that had not been reasoning from the scoreboard, executed by a fresh
session that read no prior G-D number before its own existed. Judge identity
`fd39e7b2c47fa375` (`gpt-5.5`, `base_url=https://api.openai.com/v1`,
`api_kind=openai`, `params={"reasoning_effort":"high"}`, prompt v1
`f99151e4add69b31` — byte-identical to every recorded attempt), the same
identity as the 2026-08-08 grown-gold contact, which is what the ruling's
"attempt on gpt-5.5" required. Runner, gold and bars unmodified; tree clean at
`1b4b190d`; intent row `f571aaac-8490-4f12-baac-6e2b6b73c82d` durable before
first gold contact. Preflight: `/v1/models` 200 with `gpt-5.5` listed; fixture
stage 9/9 valid, all replayed warm — the full warm replay is itself the
identity check, since only the recorded identity's cache keys could serve it.
Report: `docs/eval/2026-08-12-judge-qualification-fd39e7b2.md`.

| Bar | Required | Pooled (402) | Rule B population (176) |
|---|---|---|---|
| `groundedness_gate_precision_bar` | 0.95 | 0.9884 **PASS** | 0.9857 **PASS** |
| `groundedness_gate_recall_bar` | 0.90 | 0.9827 **PASS** | 0.9583 **PASS** |
| `contradiction_precision_bar` | 0.70 | 0.8875 **PASS** | 0.9189 **PASS** |
| `contradiction_recall_bar` | 0.95 | **0.8875 FAIL** | **0.8500 FAIL** |

**Verdict: NOT CLEARED.** Pooled contradiction-recall is 71/80 — nine misses
where the bar permits four. Rule B's population scored 34/40 — six where its
lattice permits two. Neither is an edge case, and the two populations agree, so
no pooling question arises. Six of eight bar readings pass. Invalid responses
0/402. No qualification record was minted — the runner printed "G-D stays
closed" and wrote nothing, which is the miss path working as specified.

**The stopping rule has now fired, and it forecloses every branch equally.**
T2.114's rule, written before the run and binding regardless of outcome: this
was the **final** judge attempt on this gold. G-D is recorded NOT CLEARED, no
further model is tried on this pair set, and a miss does not authorise a fourth
attempt. The only remaining moves are the owner's, and each must stand on
grounds that do not cite this result: a new gold justified independently, or a
bar argument likewise independent. "One bar missed" is not an invitation to try
again — `gold_touching_attempts` reads **2** and the budget on `4975c5cc` is
spent. The task's stopping condition is stated as **met**.

**Most of this attempt replayed warm, and that is the most important caveat in
it.** The twin: `judge_call` live n=64, cache n=338 (fixtures 0 live / 9
cache); the disk cache grew by exactly 64 entries. Because the invocation
matched the 2026-08-08 identity byte-for-byte, every pair shared with that
contact returned its stored verdict. That cuts both ways. It means the pooled
0.8875 against that run's 0.9125 is **not** judge drift — the judge cannot have
moved on pairs whose verdicts are literal replays — so the delta is census
composition (T2.115's retirements, whose overlap with the old misses the
section above records as uncomputable backward) plus 64 fresh verdicts, in
proportions no artifact can decompose backward. It also means this is not an
independent second sitting of the judge on the shared material. Forward, the
gap the 2026-08-10 entry named is closed: this run emitted the per-pair
`{pair_id: verdict}` artifact beside the cache (`entailment/verdicts/`, same
contaminated category, never published), so the next comparison **against this
run** is attributable.

**The warm-replay decomposition surfaced a census defect, recorded for the
owner rather than adjudicated here.** The 338 warm hits decompose as 226
(the contacted population) + 110 (Rule B's growth pairs, first contacted by
this same identity on 2026-08-08) + **2 pairs the census counts as new**:
`eg-0367` and `eg-0404`, whose cache entries date to 2026-08-08 15:52–15:57
UTC. Both are **byte-identical reproductions — premise and hypothesis — of
pairs their own authoring round retired**: `eg-0367` reproduces retired
`eg-0155` (direction/contradicted), `eg-0404` reproduces retired `eg-0048`
(value-swap/contradicted), both `retirement_kind: "lattice"`. Two consequences,
neither of which moves a measured number: Rule B's "not contacted before"
property is dented in substance for 2 of its 40 contradicted pairs — beyond
C-1's premise-overlap note for `eg-0367`, this is full-text identity, and the
judge was served its stored verdicts for both — and the retirement did not
retire the content, since the round's authoring reproduced it verbatim under
new ids. The verdict does not turn on this: recall fails on both populations
with or without the two pairs. Their hit/miss status is deliberately not
recorded here. Owner-adjudication item, beside C-1/C-2.

**Census independence was disclosed and its flag was silent for the right
reason.** The report carries the ruled disclosure: 80 contradicted rows over 78
independent propositions (duplicates `eg-0093`/`eg-0367`, `eg-0194`/`eg-0251`);
against 0.95 the minimum pass is 76/80 on rows and 75/78 on independent
propositions, and the bar is expressible on this census. The robustness flag
exists for one case only — a rows-**pass** the independent reading would fail —
and this run is a fail on both readings (0.8875 on rows; worst-case independent
69/78 = 0.8846), so the flag correctly did not fire. Present and silent, not
absent.

**The failure is the same rule as 2026-08-08, now measured through a mostly
replayed lens.** Pooled recall misses by slice: **value-swap 8, overreach 1**
(the census's single overreach-contradicted pair, added by the resize); Rule
B's six: value-swap 5, overreach 1. The precision errors sit on disjoint
material — temporal 7, direction 2 — the same structure as that run (whose
seven misses were all value-swap, judged `unsupported`). The weak slices are
value-swap 0.810 and temporal 0.825 against 0.96–1.00 elsewhere. The
exclusive-slot rule remains what this judge declines to apply, and the prompt
already states it — editing it would be tuning against the set that measured
the failure, barred by doc 17 §6 and now moot under the stopping rule.

**Cost twin.** Gold pass 402 calls, 196,843 tokens → **489.7 tokens/claim**;
fixture overhead 9 calls / 4,088 tokens. Latency: live p50 3.34 s / p95 7.21 s
(n=64); cache p50 ≈ 0.1 ms (n=338).

**What stays closed.** No qualification record exists;
`VerificationJudge.judge()` still refuses; the Tier-C scan still dead-ends;
Phase 3 (L3 articles) stays closed and `article_synthesis` stays a placeholder.
G-D remains open with no further attempt sanctioned on this gold.

### G-D — the per-pair verdict artifact was leaking residue (T2.122, 2026-08-12)

The paragraph above cites `entailment/verdicts/` as where this run's per-pair
artifact landed. Measured 2026-08-12: that directory held **96 files, of
which 95 were synthetic residue** written by the test suite — `VERDICTS_DIR`
was a module constant read directly at the write site with no override, so
any test driving `run_judge_qualification.py` to scoring completion under
the default (deepseek) identity wrote a stub-judge verdict file into the
live, gitignored artifact directory. 79 sat at the top level (the brief's
original count); a further 16, previously undocumented, sat in a stray
`verdicts/verdicts/` subdirectory consistent with an earlier, unfinished,
unrecorded manual quarantine attempt. Several residue files carried the
real, current gold sha and the real deepseek identity — i.e. were
indistinguishable from a genuine run by filename alone.

**Fixed**: `run_qualification` now takes a `verdicts_dir` parameter (default
unchanged for production), the test suite's `_run` helper overrides it to a
throwaway path, and a new regression test fails if the writer ever again
reads the module constant directly instead of the parameter. The 95 residue
files were identified — filename, identity, gold sha, pair count, measured
entailed precision and contradiction recall for every one — and removed only
after that identification was committed:
`docs/eval/2026-08-12-verdicts-directory-residue-removed.md`.

**The one genuine file, `2026-08-12-fd39e7b2-6eadba73.json`, is untouched.**
Its metrics reproduce this section's numbers exactly (entailed precision
0.9884, contradiction recall 0.8875), and its sha256 —
`80ac5451c080b68649ea8524a3387b126dd30f96a4f69625acf2fb8252281962` — is now
recorded both there and in
`docs/eval/2026-08-12-judge-qualification-fd39e7b2.md`, outside the artifact
itself, so R2/T2.119's re-score can authenticate its input against a value
that does not live in a gitignored directory alone.

### T2.118 — duplicate/independence pass over the non-contradicted census (2026-08-12): **entailed 173 rows over 167 independent propositions; unsupported clean; no reproduced retirements. The gate applies its bar to ROWS, with the independent reading disclosed beside it.**

Run by a party outside the census's authoring lineage, as the task requires,
against gold file sha256 `6eadba73` (417 rows: 402 live — 173 entailed, 149
unsupported, 80 contradicted — and 15 retired, all contradicted:
`eg-0048/0119/0123/0128/0142/0146/0149/0155/0162/0164/0172/0181/0214/0218/0232`).
The live counts confirm the spec's artifact-derived 173+149 from the gold
itself, so no judge output was opened. **Zero model calls, zero runner
invocations, zero gold edits** — the pass is the committed tooling the
contradicted side received: `benchlib/duplicate_propositions.py` at its
committed threshold (0.85), `judge_qualification.census_independence` for the
ruled disclosure arithmetic, byte-identity over live pairs, and text comparison
of every live non-contradicted pair against every retired pair. The checker
validated itself by reproducing the contradicted side's two known findings
exactly (live `eg-0367` byte-identical to retired `eg-0155`, live `eg-0404` to
retired `eg-0048`) before being read on the new material.

**Finding 1 — the entailed class carries five duplicated propositions, one of
them three rows wide.** Seven findings, all similarity 1.0 (token-set
identical), all `l2-fact` provenance, each differing only by an article, a
casing change, or word order — exactly the class R-B named as *"passes the
loader's uniqueness check while leaving a near-duplicate in a measurement
set"*:

| Component | Premise | Hypotheses | Slice |
|---|---|---|---|
| `eg-0051` + `eg-0322` | license-report depends on internal package mirror | "license-report depends on the internal package mirror." / "The license-report depends on the internal package mirror." | verbatim |
| `eg-0063` + `eg-0125` | jenkins deployed on ci-01 | "Jenkins is deployed on ci-01." / "It is on ci-01 that Jenkins is deployed." | verbatim |
| `eg-0078` + `eg-0307` | apps/portal uses audit-log | "audit-log has at least one consumer." / "The audit-log has at least one consumer." | weakening |
| `eg-0083` + `eg-0247` | config management agent causes lp-relay | "lp-relay is brought about by the config management agent." / "The lp-relay is brought about by the config management agent." | paraphrase |
| `eg-0094` + `eg-0279` + `eg-0323` | billing-sync deployed on apps-02 | "billing-sync is deployed on apps-02." / "On apps-02, billing-sync is deployed." / "Billing-sync has been deployed on apps-02." | verbatim |

So the entailed census is **173 rows over 167 independent propositions** (six
redundant rows across five components). The aggregate was technically on the
record — R-B's 2026-08-10 entry says its check "reports nine duplicate
relations … seven are `entailed`" — but the seven were never itemised, never
adjudicated, and never disclosed in any run artifact: the runner computes
`census_independence` for the contradicted class only
(`run_judge_qualification.py:370`). This is their first itemisation. The
mechanism mirrors the contradicted side's: five of the six redundant rows are
growth-round pairs (`eg-0242`+, the T2.110/T2.115 authoring lineage) authored
over premises that already carried a live pair.

**Finding 2 — the committed collapse arithmetic is wrong on this class, by
one, in the direction that misstates worst-case robustness.**
`census_independence` computes `independent = rows − len(findings)`, treating
each finding as one collapse. The `eg-0094`/`eg-0279`/`eg-0323` triangle
produces **three** findings but only **two** collapses, so the committed
function reports 166 where the true count is 167. Both contradicted components
were two rows wide, so nothing exposed this before; the entailed class is
where it first binds. Consequence for R2's mint path, which reuses this code:
the disclosure would print 166, and the report's worst-case-independent
computation (`hits − collapsed`) would over-collapse by one. Recorded here for
T2.119/T2.117 to handle; this task edits no code by its own charter.

**Finding 3 — Rule B's "not contacted before" property is dented for five of
its 72 entailed rows,** more widely than the contradicted side's single
`eg-0367` case: `eg-0322`, `eg-0307`, `eg-0247`, `eg-0279` and `eg-0323` are
Rule B rows restating propositions the judge met in the contacted population
(`eg-0051`, `eg-0078`, `eg-0083`, `eg-0094` — the last twice). The bytes were
new; the propositions were not. Within the Rule B population itself one
duplicate pair is fully internal (`eg-0279`+`eg-0323`), so Rule B's entailed
census is **72 rows over 71 independent propositions**. `eg-0063`+`eg-0125`
sits fully inside the contacted population.

**Finding 4 — the unsupported class is clean.** 149 rows, zero duplicate
findings at the committed threshold, zero byte-identical pairs: **149 rows =
149 independent propositions**, rows and independent readings coincide.

**Finding 5 — no reproduced retirements on the non-contradicted side.** No
live entailed or unsupported pair matches any of the 15 retired pairs
byte-for-byte, and the one near-duplicate flag was examined and dismissed:
live `eg-0266` (entailed, verbatim: "Astro replaces MkDocs.") against retired
`eg-0162` (contradicted, direction: "MkDocs replaces Astro.") scores 1.0 only
because the checker discards word order — they assert **opposite**
propositions under opposite verdicts, a reversal, not a reproduction. The
defect class the contradicted side turned up (retired content re-entering
under a new id) does not occur here.

**Finding 6 — no cross-verdict label conflicts.** A check the committed tool
cannot run (it groups by verdict, on purpose) was run once as diligence: same
premise, hypotheses at similarity ≥ 0.85, one row `entailed` and the other
`unsupported`. Five flags, all similarity 1.0, all the same shape — a
`verbatim` restatement beside its `direction` reversal of non-exclusive `USES`
(`eg-0042`/`eg-0282`, `eg-0074`/`eg-0283`, `eg-0079`/`eg-0141`,
`eg-0151`/`eg-0269`, `eg-0185`/`eg-0305`). Reversals assert different
propositions; different verdicts are correct. All dismissed; the corpus's
deliberate hard negatives are intact, not duplicated.

**The minimum-pass arithmetic, on both readings.** The census-denominator bar
for the entailed class under R1 is `groundedness_gate_recall_bar` = **0.90**
(precision's denominator is judge-dependent; the unsupported class is no
barred metric's denominator — its rows enter precision only as false-accept
candidates, and it carries no correlated structure to bank there).

| Census | Rows reading | Independent reading |
|---|---|---|
| Entailed, pooled | **156/173 = 0.9017** | **151/167 = 0.9042** (committed arithmetic would print 150/166 = 0.9036) |
| Entailed, Rule B | **65/72 = 0.9028** | **64/71 = 0.9014** |
| Unsupported, pooled (no bar; shown at 0.90) | 135/149 = 0.9060 | same — rows = propositions |

The bar is **not expressible on rows** for any of these censuses: 0.90 falls
between lattice values everywhere (pooled entailed enforces 0.9017, +0.17pp of
quantisation). T2.110 sized only the pooled *contradicted* census onto its bar
(76/80 = 0.9500 exactly); no such sizing was ever run for the entailed class,
and per the fd39e7b2 report's own words, where the lattice enforces a stricter
number the verdict is evidence about the census, not only the judge.

**Robustness at the margin, stated before any re-score exists.** A rows-pass
at exactly the minimum 156/173 whose judge caught all six redundant rows has a
worst-case independent reading of **150/167 = 0.8982 — below the bar**. At
157/173 and above, the worst case is 151/167 = 0.9042 and the pass is robust.
On Rule B the minimum 65/72 is already robust (worst case 64/71 = 0.9014, one
internal collapse). So the same eyes-open easing the owner's 2026-08-12 ruling
accepted for the contradicted class exists on the gated class, and it bites
only in the exact-minimum row: the disclosure-plus-flag machinery is the right
shape for it, once extended to this verdict class.

**Which reading the gate stands on: ROWS.** The owner's 2026-08-12 ruling —
independence is handled by reporting, not retiring — set that for the
contradicted class, and nothing in this pass licenses a different regime here:
the bar applies to rows (156/173 pooled, 65/72 Rule B for entailed recall at
0.90), the independent reading (151/167, 64/71) is disclosed beside it, and an
exact-minimum rows-pass must self-flag as not robust to the independence
reading rather than read as a clear pass. The ruling's text names only the
contradicted class, so its extension to the entailment class — and the
component-arithmetic fix in Finding 2 — are conditions T2.119's mint must
carry, not things this pass may assume. **The unsupported side is clean on
every probe; the entailed side carries the contradicted side's duplicate
defect in larger degree (5 duplicated propositions vs 2, one of them
three-wide) and none of its worse one (no reproduced retirements, no label
conflicts).** No gold file was modified by this pass.

### G-D redesign: **RATIFIED by the owner, 2026-08-08**

The recommendation below is adopted. Tier-3 amendments applied to
`docs/design/08-temporal-lifecycle-consolidation.md` §4.2 (the LLM scan leaves the veto's
inputs and becomes a review opener) and `docs/design/17-test-and-eval-harness.md` §6 (the
contradiction metric pair inverts with its consumer). Implementation is T2.109; the
follow-on preconditions are T2.110 (grown gold) and T2.111 (G-C re-measure under the new
shape).

**The bars, stated 2026-08-08 by the controller under delegated authority.**
`contradiction_recall_bar` = **0.95**, `contradiction_precision_bar` = 0.95 → **0.70**.
Derived, not measured: doc 17 §6's rule — truth-critical metric at 0.95, the other at 0.90
— predates every judge run. **Refined 2026-08-12 (T2.121):** the phrase this section used to
carry — "the amendment is what made recall truth-critical" — was loose. A recall miss's cost
was truth-critical before T2.109 and is truth-critical after it; nothing about the amendment
changed what a miss costs. What the amendment changed is **precision's** class: precision left
the truth-critical bucket because its consumer (the absolute veto) moved to the deterministic
arm, leaving recall the only truth-side metric left on the LLM-judge arm. Same bar, cleaner
reason: recall takes 0.95 by that rule because it always sat in the truth-critical class, not
because the amendment moved it there. **The check that this is a derivation and not a fit is that the
measured judge does not clear it**: gpt-5.5 scored contradiction-recall 0.945, so a bar
chosen to launder that number would sit at 0.90, and `test_contradiction_recall_is_gated_and_barred_by_derivation`
pins the bar *against* 0.90 for exactly that reason. Precision drops because its consumer
changed and not because it was missed — a false flag now costs a reviewer a minute rather
than a wrong belief, so the bar need only keep the queue workable (noise under one flag in
three); left at 0.95 it would price precision as truth after §6 stopped doing so.
**Granularity binds:** at the retired gold's 55 contradicted pairs recall resolves in steps
of 0.018, so 0.95 and 0.945 are one measurement — T2.110's census must make 0.95
distinguishable or the bar is stated but not measurable. Disclosed plainly because it
matters: the controller had already seen both judges' results when deriving these, which is
why the derivation is written out rather than asserted, and why both remain the owner's to
move with a recorded argument. Neither may be moved to make a run pass.

**What ratification did not do on its own: supply the bars.** `contradiction_recall_bar`
is the truth-critical bar under the new shape and **has no default and no value** — the
gate fails closed until the owner states one. That is deliberate and structural rather
than conventional: both measured judges' numbers are public in this file, so a default
chosen now would be a bar chosen while looking at them, which is the one thing that would
make the re-qualification worthless. `contradiction_precision_bar` is retained as a
review-load floor and its value is equally the owner's to restate, since 0.95 was derived
for a deciding consumer that no longer exists on that arm.

**G-D stays open.** Nothing about this ratification clears it; it changes what clearing
would mean, and the measurement runs on T2.110's gold, not this one.

### The 0.90 contradiction-recall re-derivation: rejected (2026-08-12, T2.121, ruling R3)

A session proposed re-deriving `contradiction_recall_bar` from 0.95 down to 0.90, arguing that
post-T2.109 a recall miss costs an unopened review item rather than a wrong belief — the same
argument that already carried `contradiction_precision_bar` down to 0.70. **That derivation is
wrong and is rejected.** `contradiction_recall_bar` stays **0.95**.

The argument does not survive contact with what a recall miss actually is under the amended
veto. A recall miss is a genuinely contradicted fact that keeps `corroborated`, keeps a badge
asserting no known contradiction, and stays citable by articles — a standing wrong belief with
no backstop, since the human-verdict arm (`rejected_after`) is the scan's only route into the
audit and the deterministic arm is corpus-vacuous today. A precision miss is bounded: a
reviewer opens the flagged fact, finds nothing wrong, and dismisses it in a minute. The two
misses are not the same size, and that asymmetry — unchanged by T2.109 — is exactly what
doc 17 §6's rule already prices: 0.95 for the truth-critical metric, 0.90 for the load metric.
Recall did not move classes when precision did.

**Why this is recorded rather than dropped quietly, with the arithmetic.** At a 0.90 bar the
2026-08-10 deepseek re-measure (table above, `gate-ledger.md:1122-1127`) clears **all four
bars on both populations**: contradiction recall 0.9375 pooled and 0.9500 Rule B, both above a
0.90 line, with the other three bars already passing at every reading on that run. The
proposal was presented as harmless bookkeeping; it is not — it would have converted a recorded
**NOT CLEARED** result into a retroactive **PASS**, on a run whose two-attempt budget on this
gold is already spent (T2.115 followed by T2.114's final attempt, both NOT CLEARED). A reader
who believed the 0.90 derivation would conclude G-D cleared on 2026-08-10; it did not, and does
not now. This entry exists so the same derivation cannot resurface at the next gold looking
new.

**No bar value moves.** `contradiction_recall_bar` remains 0.95, `contradiction_precision_bar`
remains 0.70. G-D remains open, unchanged by this correction.

### G-D resolution (2026-08-08, resolution spike): the defect is the veto's architecture, not the judge

**Verdict — of the four possible resolutions (clearable / bar wrong / veto architecture
wrong / not resolvable now): the veto's architecture is wrong.** Specifically: wiring the
LLM judge's verdict directly into the absolute dispute veto, and gating that wiring on a
single precision metric, jointly demand a judge no measured configuration provides and
reward a judge that goes quiet. The gate stays open; nothing was minted; this run made
**zero live model calls** — every number below is an offline replay of the cache at
`backend/scripts/benchlib/entailment/cache` (both qualifying runs' calls are cached), no
`--gate` invocation, no new gold contact through the runner.

**New measured evidence (cache replay, live_calls == 0).**

- **Per-pair verdicts of both counted attempts were recovered from the cache.**
  deepseek-v4-flash by exact cache-key reconstruction (241/241 pairs resolved, recomputed
  contradiction-precision 0.7937 — equal to the report). gpt-5.5 by token-checksum
  attribution (the cache stores no request text, so files were attributed to pairs via
  o200k tokenization: expected prompt-tokens = 309 + user-message tokens for prompt v1,
  +162 for v2). The attribution is over-determined: all four serving-invariant token
  totals reproduce exactly (v1 gold 82150/37202, fixture 3041/966; v2 gold 121192/34449,
  fixture 4499/994), the v1 confusion table reproduces the published report cell-for-cell
  (52/3 · 101 · 7/2/76), and the recovered v1 false-positive set independently reproduces
  the 7 ids the T2.41 follow-up had already identified.
- **The two vendors' false positives overlap on exactly three pairs, and they are the
  same failure.** deepseek: 13 FPs (11 `direction`, 1 `overreach`, 1 `temporal`).
  gpt-5.5: 7 FPs (4 `temporal`, 3 `direction`). Intersection: eg-0023 (load-balancing
  roles), eg-0075 (`USES`), eg-0163 (`CAUSES`) — all three are reversals of
  **non-exclusive** relations, gold-`unsupported` under the reversal rule's non-exclusive
  case, all `adjudicated`/owner-ruled labels. On eg-0023 the blind resample record shows
  **both independent human passes made the same `contradicted` error the models make**
  (the owner ruling corrected them). The exclusion-vs-absence distinction on reversed
  non-exclusive relations sits at or past the blind human ceiling, not just the model one.
- **The most precision-favouring composition available from every judge this project has
  measured still fails, and cannot pass.** A conjunctive two-vendor veto — dispute only
  where *both* judges say `contradicted`, assembled post-hoc with full knowledge of both
  error sets, i.e. the best case any ensemble of these judges could reach — measures
  precision 48/51 = **0.9412**, recall 48/55 = 0.8727. With the 3 shared FPs its
  precision ceiling is 55/58 = **0.9483 at any recall**: no true-positive count that
  exists can clear 0.95 over those three errors. (Diagnostic only: as a qualification
  this arrangement would be contaminated by construction — it was fitted on a
  three-times-contacted gold.)
- **The single-metric gate is incoherent for a veto consumer, measured, not argued.**
  Replayed through the shipped scorer (`judge_qualification.score_judgments` +
  `bar_results`): a judge that emits `contradicted` on exactly one correct pair and
  `unsupported` elsewhere scores contradiction-precision 1.0, leaves entailed P/R
  untouched, and **passes all three gated bars at contradiction-recall 0.0182**. Only
  total silence fails (precision over zero acceptances is None → fail).
  `BAR_METRICS` carries no recall key, so the gate as specified qualifies a near-mute
  judge to hold an absolute veto while scoring the measured 0.88-precision /
  0.95-recall judge as a failure. Run 3 walked this gradient by accident; the scorer
  replay shows the end of the gradient is a pass.

**Why the other three resolutions are not it.**

1. *"G-D is clearable as specified"* — no. Three counted runs, two vendors, one frozen
   prompt: 0.7937 / 0.8814 / 0.9020. The one principled prompt fix was measured and
   reverted (+0.02 precision bought by −0.11 recall). The two-vendor conjunction sits at
   0.9412 with a 0.9483 ceiling. Model-shopping past two attempts is barred (doc 17 §6),
   and the failure is task-shaped — both vendors, and the blind human passes, err the
   same way on the same distinction.
2. *"The bar is wrong — lower it"* — no. The 0.95 was **inherited**, not derived: doc 17
   §6 derives 0.95 for *entailed* precision (a hallucination shipping under a badge) and
   then says "the veto consumer inherits the same qualification". Derived from the veto
   consumer's own cost function, the bar should be *higher*, not lower: a scanned FP
   dispute is near-permanent (`detect_scanned_contradiction` — the scan never re-checks
   a disputed fact; the exits are guard-lapse or human ratification), demotes a
   correctly-corroborated fact, and serves it `disputed` to every consumer. Lowering the
   bar to the measured 0.88 would license ~7 manufactured near-permanent disputes per
   241 checked pairs into an instrument that beats any corroboration count. The bar
   number is not the defect; the consumer that demands it is.
3. *"Not resolvable now"* — no. The evidence above is sufficient to resolve the design
   question; what remains is ratification (below), not measurement.

**The recommended design — owner's to ratify, Tier-3 (it amends doc 08 §4.2 and
doc 17 §6).** The architecture already contains two arms with opposite precision
profiles, and the fix is to pair each arm with the consumer its profile supports:

- **The absolute veto stays absolute — on the deterministic arm only.**
  `detect_open_contradiction` decides from the closed vocabulary with no judgment;
  its precision is by construction, which is what an unappealable instrument requires.
  No migration burden exists: the LLM arm has never fired in production (dark behind the
  unqualified judge), so no scanned dispute anywhere needs re-adjudication.
- **The LLM scan's finding opens review instead of disputing.**
  `detect_scanned_contradiction` leaves `CONTRADICTION_DETECTORS`; the scan's journalled
  verdict drives a new review opener (doc 08 §6 gains a fourth opener,
  contradiction-suspected). The fact keeps its rung and its badge while flagged; a human
  confirming the flag disputes it through the already-live human door
  (`human_adjudication.reject_fact`). Doc 08 §5.3's own asymmetry licenses this: a flag
  awaiting confirmation is a *delayed* dispute — the sanctioned direction of error —
  where the current wiring converts every judge FP into the failure the asymmetry
  forbids. Relative to the shipped state (an arm that finds nothing) review-opening is
  strictly more detection; relative to the aspirational state it trades automatic
  demotion for human latency, bounded by review cadence.
- **The qualification metric pair inverts with the consumer.** For a surfacing
  instrument, contradiction-**recall** is the truth-critical bar (a missed contradiction
  never reaches a reviewer — and recall is precisely what the current gate lets go to
  0.018) and precision becomes a review-load floor (at the measured 0.88, ~1 in 8
  flags is noise — a queue-economics number, not a truth number). The new bars are the
  owner's to state **in advance** of the next gate run; this spike deliberately states
  none, because both measured gpt-5.5 numbers are known and a bar chosen now would be
  chosen looking at them. The re-qualification must run on T2.54-grown gold — this gold
  has 3 recorded contacts and its FP census is now fully public in this file.
- **What stands unchanged:** the `disputed` rung, the conjunctive recovery, the
  hysteresis, `_write_born_rung`, human-only `confirmed`, and the G-C false-promotion
  audit. The audit's machine arm changes shape (review-confirmed human rejections
  instead of raw machine disputes — better-attributed evidence), so the G-C→G-D
  cross-edge analysis must be re-read under the new shape before G-C is re-attempted.
- **Costs, stated:** a review queue nobody works is a dispute deferred forever — the
  precision floor is what keeps the queue workable, and the queue consumer becomes
  load-bearing for contradiction handling; and doc 08 §4.2's sentence naming the LLM
  scan a veto input is amended, with §4.3's flowchart keeping its dispute node for the
  deterministic arm only.

**If the owner rejects the redesign and keeps the current specification:** then the
honest answer to this gate is that nothing this project can lawfully do clears it — no
measured judge, no lawful prompt change, and no ensemble of the judges measured reaches
0.95 on this census, and the two lawful remedies (a third model, more gold) are
respectively barred and unable to remove the shared-error class the blind human passes
also fell into. That is a result, and this file records it as one.

### G-D verdict: **NOT CLEARED** — two vendors, one bar (2026-08-08, T2.41)

**Attempt 2: `gpt-5.5` at the same frozen prompt** (identity `1bb9d9bae62eb9d8`,
`prompt_sha f99151e4add69b31` — unchanged from attempt 1, which is what makes the two
comparable). Doc 17 §6's sanctioned remedy for a missed bar is a different judge model at
a frozen prompt; this is that, and `gold_touching_attempts: 2` records it. Report:
`docs/eval/2026-08-08-judge-qualification-1bb9d9ba.md`.

- entailed-precision **0.9806** ≥ 0.95 — **PASS**
- entailed-recall **1.0000** ≥ 0.90 — **PASS** (101/101, zero false rejects)
- contradiction-precision **0.8814** vs 0.95 — **FAIL**

**gpt-5.5 is markedly the better judge and still misses.** `direction` accuracy rises
0.567 → **0.900**, entailed-recall 0.931 → **1.000**, and manufactured disputes fall from
13 to **7**. The residual is 7 gold-`unsupported` pairs called `contradicted` against 52
true positives. At 55 gold-contradicted pairs the 0.95 bar permits at most **two** false
positives (52/54 = 0.963; 52/55 = 0.945), so the bar is effectively "at most two
manufactured disputes in 241 pairs".

**The finding is about the task, not the model.** Two frontier models from two vendors,
same frozen prompt, fail the same bar in the same direction — over-calling contradiction
on pairs the premise merely fails to assert. That is the exclusion-vs-absence distinction
the rulebook's own "Contradiction requires exclusion, not absence" clause exists for, and
it is the distinction the production veto depends on being right about, since one non-echo
contradiction beats any corroboration count with no config on its path. A judge that
manufactures 7 disputes per 241 claims would, unqualified, be a live source of false
`disputed` transitions.

**A prompt fix was tried, measured, and reverted — record it so it is not redone.**
The prompt referenced "a reversed relation when the relation is exclusive in direction"
without ever saying which relations qualify; the gold decides that from a 16-row table
the judge has never seen. That gap was real: enumerating both classes from the taxonomy's
own semantics took `direction` from 0.900 to a perfect **30/30**. But the same edit made
the judge broadly reluctant to call contradiction at all, and `value-swap` collapsed
**0.897 → 0.690**. Net (`docs/eval/2026-08-08-judge-qualification-7779f3dd.md`, run as a
diagnostic against a non-canonical record path so it could not mint):

| | v1 | v2 |
|---|---|---|
| contradiction-precision | 0.8814 | 0.9020 |
| contradiction-**recall** | 0.945 (52/55) | **0.836 (46/55)** |
| `direction` | 0.900 | 1.000 |
| `value-swap` | 0.897 | 0.690 |

Precision improved **only because the judge predicted contradiction less often** — false
positives 7 → 5 while true positives fell 52 → 46. Reverted to v1, so the identity the two
recorded attempts measured is the shipped one.

**The gate rewarded that trade, and that is a gate-design finding.** Contradiction
*recall* is computed on every run and carries **no bar**; only precision is gated. So a
change that trades recall for precision reads as progress on the one number the gate
watches while making the judge worse at its job — missing 9 contradictions of 55 instead
of 3. One unplanned edit walked straight into it. Before the next attempt, the owner
should decide whether contradiction-recall gets a bar of its own (or the pair is gated on
an F-measure); optimising an absolute veto on precision alone selects for a judge that
stays quiet.

**Local prompt edits have non-local effects.** The direction enumeration was defensible in
isolation, sourced from the taxonomy rather than from the observed errors, and it still
broke an unrelated slice. Any future prompt work needs the whole slice table read before
and after, not just the metric being chased.

**Stopping here rather than trying a third model.** Two attempts at a frozen prompt is the
remedy; an open-ended sweep until one clears is tuning-against-gold by another route, and
the harness counts contacts precisely so that is visible. The remaining honest moves are
the owner's: grow the gold's contradicted census so the bar has headroom that is not
single-error resolution; or re-examine whether 0.95 on contradiction-precision is the
right bar, which is a bar change and needs its own recorded argument, not a quiet edit.

**A same-day report collision was fixed here.** Attempt 2 overwrote attempt 1's report —
the path was date-keyed only, and two attempts in a day is the *normal* shape of a missed
bar. Attempt 1 survived solely because it had already been committed. Report paths now
carry the judge identity hash, and both attempts are preserved:
`-4d886440.md` (deepseek-v4-flash) and `-1bb9d9ba.md` (gpt-5.5).

#### Attempt 1 — `deepseek-v4-flash` (2026-08-08)


**Two bars of three cleared; the contradiction bar missed by a wide margin, and it is
the one the veto consumer depends on.** Run against gold v1 at 241 live pairs
(`sha256 e6d5647a…`), judge identity `4d886440a646f176` (`deepseek-v4-flash`, prompt v1),
`gold_touching_attempts: 1`, invalid responses 0/241. Full report:
`docs/eval/2026-08-08-judge-qualification.md`.

- entailed-precision **0.9895** ≥ 0.95 — **PASS**
- entailed-recall **0.9307** ≥ 0.90 — **PASS**
- contradiction-precision **0.7937** vs 0.95 — **FAIL**

**The failure is the one T2.26 predicted, at scale.** 13 gold-`unsupported` pairs were
judged `contradicted` — manufactured disputes — against 50 true positives. The interim
run's 0.818 on 41 pairs was dismissed as unresolvable at that size (one error moved it
0.09); at 241 pairs the granularity objection is gone, and the number went *down*. The
`direction` slice carries it: **0.567 accuracy (17/30)**, against 0.97+ on `overreach`,
`paraphrase`, `verbatim` and `unrelated`. The judge reads an unasserted reversal as an
excluded one.

**What this closes.** G-D stays open, so Phase 3 (L3 articles) stays closed and no
qualification record exists — the runner wrote none, by the rule below.
`VerificationJudge.judge()` therefore continues to refuse unconditionally, which keeps the
machine's contradiction arm dark and, through the G-C→G-D cross-edge ratified 2026-08-07,
leaves G-C's false-promotion audit unable to produce a systematic number. **E2 cannot
close on this run.**

**A failed gate run no longer mints the record it would have opened (fixed 2026-08-08).**
This run wrote `app/services/verification_qualification.json` carrying its own failing
metrics and `gate_eligible: true`. Nothing was qualified by it — `qualification_state`
re-checks every metric against its bar at read time and refused — but the artifact sat at
the canonical path, and a bar is a `config` row: loosen one and the key turns. The G-C
driver had always stated the opposite rule for its own record ("written only by a run
whose verdict cleared … never as a side effect of measuring"); the two gates now agree.
The record was deleted and the runner will not write one on a miss.

**Do not fix this by tuning the prompt against this gold.** A prompt edit moves
`prompt_sha`, hence the judge identity, hence de-qualifies mechanically — and tuning
against the set that measured the failure is the contaminating loop T2.26's plan review
flagged as its one Critical. A re-attempt needs either a different judge model at the same
frozen prompt, or gold growth authored independently of these 13 errors.

**Interim measurement (T2.26, 2026-07-31) — not a gate verdict.** One counted run of the
qualified-judge candidate (`app/services/verification_judge.py`; model
`deepseek-v4-flash`, identity `66df91cee44d2415`, prompt v1 frozen at fixture-pass before
first gold contact; `gold_touching_attempts: 2` = one live pass + its warm verification
replay), against gold v1 (`sha256 3fd42fc0…`, 41 live pairs), recorded in
`docs/eval/2026-07-31-judge-qualification.md`:

- entailed-precision **1.000** (17/17 accepts, zero false accepts) — above bar
- entailed-recall **1.000** (17/17) — above bar
- contradiction-precision **0.818** (9/11) — **below its 0.95 bar**: two `unsupported`
  `direction` pairs judged `contradicted` (the manufactured-disputes failure);
  contradiction-recall 0.900 (one missed `temporal` contradiction); invalid 0/41
- twin: **408.2 tokens/claim** on the gold pass (16,736 tokens / 41 claims, fixture
  stage excluded); live judge-call latency p50 1.07 s / p95 1.27 s (n=41, powered)
- granularity at this size: 17 gold-entailed means one false accept ≈ 17/18 = 0.944,
  so the precision bar is effectively "zero false accepts"; 10 gold-contradicted means
  one manufactured contradiction ≈ 10/11 = 0.909 — single-error resolution, which is
  why the set must grow before a verdict means anything

**Interim only — gate not claimable:** `run_judge_qualification.py --gate` refuses this
gold before any model call (composition: 41 < 200 live pairs; `l2-fact: 0/41`;
author-labelled: 41/41), no app-side qualification record exists (its absence is
test-pinned), and the verdict is T2.41's after T2.54. Under the 2026-07-31 amendment's
reading, §11's real-material requirement reaches the claim/fact gold's *premise* side
(`l2-fact`); the hypothesis side remains hand-authored indefinitely for this variant —
T2.41's verdict must state composition in those terms and not overstate it.

**Gold set:** built in T2.25, **before** the judge, so the judge cannot be tuned to its
own test. *(Corrected 2026-07-31 to match the two amendments logged in
`tasks/E2-truth-core.md` that date:)* both material sources this paragraph originally
named were verified unavailable at T2.25's branch point — `article_synthesis` is a
`PlaceholderJobRunner` until T3.02 (behind this gate) and `knowledge_triples` has no
producer until T2.10 — so the seed set is 41 hand-authored pairs (16 anchored verbatim
to the retrieval corpus, machine-checked), with `synthesis-draft` and `l2-fact`
provenances reserved at test-pinned zero. Doc 17 §11 makes composition gate-binding:
synthetic-only gold is rejected, so growth to ≥ 200 pairs with real `l2-fact` premises
and full re-adjudication is T2.54's (after T2.10), and this gate cannot open before it.

**Consequence of a miss:** E3 stays closed. Below the bar, no L3 article ships as grounded —
enforced in code, not by policy: the mechanism half landed in T2.26 (the only door to the
`verification` purpose is the judge's qualification-gated `judge()`, scan-enforced; the
record only a canonical-gold `--gate` run can mint), and the ship-path half is T3.03's.

---

## T2.124 frame — owner ratification, sitting 1 (2026-08-13)

Recorded per the governing plan's step 0 Catch
(`docs/superpowers/plans/2026-08-12-t2.124-fresh-entailment-gold.md` §5), **before
step 1's commit and before any pair exists**. That ordering is the point: a sizing
ratified after pairs are authored is a sizing fitted to them.

**Ratified — items 1, 2, 3.**

1. **The derivation rule**, as §6 states it and as the committed script must implement
   verbatim: T2.25's frozen pre-judge slice proportions (verbatim 4 / paraphrase 6 /
   weakening 5 / temporal 6 / direction 5 / overreach 6 / value-swap 5 / unrelated 4,
   sum 41) scaled by largest remainder with **all** tie-breaks alphabetical; per-slice
   verdict splits from T2.25's own splits counted mechanically off pairs
   `eg-0001`–`eg-0041` with retirement flags ignored (retirement is post-judge
   information); the minimal-adjustment rule for mixed slices subject to contradicted
   = **80** (T2.110's ratified size, 76/80 = 0.9500 exactly) and entailed ≡ 0 (mod 10)
   (the 0.90 lattice); rule 3's minimum-total form, which emits **T = 280**. The
   worked matrix is ratified as *the rule's arithmetic and not the object* — the
   emitted matrix is sitting 2's, at step 6.
2. **The archive move** (D1) and the LABELLING.md round section.
3. **The justification text** (§2) as the recorded grounds: publication contamination,
   standing alone. The lattice ground is corroborating only, and the plan review
   verified that 156/173 = 0.9017 is computable from the census size and the bar with
   no judge output involved — census arithmetic, not a laundered score.

**Ruled — items 4, 5, 6.**

4. **Resample model: `deepseek-v4-pro`**, the precedent. Ruled with the foreclosure
   stated in front of the choice rather than discovered after it: whichever model
   certifies this gold acquires the resample-circularity objection as a T2.125 judge,
   so this spends v4-pro and **preserves `gpt-5.5`** — the stronger measured
   entailment performer — as a judge candidate.
5. **Premise scope: full exclusion of the old premises.** The default, not the named
   weakening. Publication contamination transfers through a premise to the
   propositions it determines: for `verbatim` the hypothesis is a near-literal
   restatement and for `direction` it *is* the reversal, so a fresh pair on a
   published premise is either a digest hit or an `eg-0367`-class near-verbatim
   reproduction. Accepted cost: rule 3 gates feasibility on the fresh harvest's yield,
   so a thin harvest **stops the round** rather than shrinking it.
6. **Branch: a task branch, merged whole at completion.** The sanctioned red — no
   `entailment/gold.json` at the canonical path between the archive commit and the
   closing floor re-assertion — never touches the working branch.

**Two code-level findings bind this round and are steps, not notes** (from the
superseded second plan's review, `docs/planning/reviews/2026-08-13-t2.124-plan-review.md`;
they are facts about `entailment_gold.py` and the refusal suite rather than about any
frame): three refusal tests read the canonical gold path and go red at the archive, and
the digest-truncation pin is destroyed by that same archive, silently disarming 414 of
415 content refusals. Both are repaired before the archive, never improvised during it.

**Not ratified here, and deliberately:** the emitted matrix (sitting 2, step 6, a
bounded yes/no on three mechanical checks), and anything requiring the fresh harvest,
which does not exist yet.

### Sitting 2 — the emitted matrix, RATIFIED 2026-08-13

**Ratified: T = 280, contradicted 80 / entailed 110 / unsupported 90.** Pair authoring
(step 7) is open from this ratification and was closed before it. From here a "no"
loops through a rule amendment via sitting 1's channel — **never** a hand edit of the
matrix.

The owner saw exactly the three things §5 fixes, each verified by a reviewer outside
the authoring lineage:

1. **Byte-regeneration: identical**, sha `ae11bc172bac05e7`, produced through the
   reviewer's own driver rather than the script's verify path. The pin was then
   *proved* to bite: a planted hand edit that leaves the census and slice sums
   consistent still fails `test_committed_frame_regenerates_byte_identically`.
2. **Asserted checks green by test** (17 passed), read off the committed file with
   `RESAMPLE_N` = 93 and `MIN_GOLD_PAIRS` = 200 resolved from source, not retyped.
3. **The matrix is the ratified rule applied to the committed inputs**, re-derived
   independently. The mixed-slice adjustment — the step the plan's own history flags as
   a contamination channel, because round 3's tie-break preference came from a party who
   had read the failure profile — is **forced, not preferred**: 12 moves is provably
   minimal, the entailed lattice forces exactly 6 to be E→C, and `SLICE_VERDICTS` forces
   all 6 into `temporal` as the only entailed-bearing mixed slice. The remaining 6 land
   in `direction` by the alphabetical tie-break alone. Nothing prefers temporal; the
   closed vocabulary compels it.

**Feasibility:** 163 fresh facts after exclusion against the rule's floor of 44.

**One tension named here rather than left for an audit, and left standing by owner
ruling.** Item 4 of the sitting-1 record above cites `gpt-5.5` as "the stronger measured
entailment performer" — a **measured judge comparative inside a round artifact**, on a
surface §2's discipline otherwise keeps score-free. It stands, deliberately: it is the
honest rationale for a ruling the owner made, and the resample choice could not be made
knowingly without it. Blindness is unharmed — the ledger is denylisted for every
authoring and labelling party, so no author or labeller can reach it. Recorded so the
next audit finds a decision rather than a leak.

**Two record corrections from the same review**, neither consequential and both landed:
the plan's near-miss share is 27/41, not 26/41 (scale-invariant, so the constraint held
either way), and U3's residual now has a shape — `cross_gold_near_overlap` screens the
archive's **live** pairs only, so a *rewording* of one of the 15 lattice-retired pairs is
unscreened while byte-identical reuse of all 415 is still refused by the digest pin.

### The contamination screen — created 2026-08-13 (Tier-1 amendment to the plan)

The plan's step 1 Catch names a controller-only screen at
`scripts/benchlib/entailment/frame_contamination_screen.txt`. **It did not exist**
anywhere in the tree — the plan was its only mention — so step 1's Catch was
unrunnable as written. Created by the controller before any brief was issued, since
the plan's standing rule is that the screen runs over every dispatch brief *before*
the brief goes out.

**Scope, decided here because the plan did not state it.** The screen runs over (a)
the **byte-prefix strip** of `LABELLING.md` — the bytes pair authors and blind
labellers actually read, i.e. everything above `## History` — and (b) every dispatch
brief addressed to an authoring or labelling party. It does **not** run over the
`## History` sections or over this ledger: neither is inside the strip, and both are
controller/owner-facing by design. A screen pointed at text nobody blind reads would
manufacture hits and get ignored.

**A first, blunter version was discarded** after it returned 66 hits on the strip —
firing on pair ids cited as worked examples and on the words "precision"/"scored"
inside rule text. Those are the recorded T2.110 residual, not leaks, and a screen
that always fires is a screen nobody runs. The committed patterns match only what a
measurement looks like.

**Baseline residual on the strip, enumerated 2026-08-13 so a reviewer can tell growth
from what was already there. Corrected the same day — the first enumeration was
half noise.** The decimal pattern was written as `[0-9]\.[0-9]{3,}`, which matches a
**task id**: `T2.115` reads as `2.115`. That fired on lines 255, 307, 411, 544 and
698 — every one a citation like "ratified 2026-08-10, T2.115" — and it also stopped a
real step-2 dispatch, because the worktree path `.worktrees/t2.124` matches too. It
failed safe, but a screen that cries wolf is one the next executor learns to wave
through, and an enumerated baseline containing noise defeats its own purpose: a
reviewer cannot tell growth from a false positive. The pattern is now
`(^|[^A-Za-z])[0-9]\.[0-9]{3,}`, which still catches ` 0.9017` and `scored 0.945`
while ignoring letter-prefixed ids.

**The corrected baseline is five lines** — LABELLING.md 369, 395, 508, 521, 701 — and
every one is a **bar value, census arithmetic, or an identity**: gold sha `98fc4b49`;
`0.95` as the stated bar beside a census of 78; `×200/41` and `131/200` as
composition; judge identity `fd39e7b2` and its contact fact. **No measured score is
above the cut**, which independently corroborates §4's re-verification after the B1
relocation. That is a narrower claim than "the strip is clean" and it is the true
one: the strip carries identities and bars, and the plan never claimed otherwise. A
hit outside these five is a finding.

### The round record — grounds, parties, firewall (step 1, 2026-08-13)

**Grounds, as ratified (item 3 above), restated where the round's execution is
recorded:** publication contamination, standing alone — the retired set's censuses,
duplicate findings and per-slice decompositions are on the public record in this
ledger and the dated eval reports, so no future qualification on those pairs could be
told apart from authorship-with-answers, independently of anything any run produced.
The entailed class's missing lattice sizing is recorded as corroborating only.
Nothing in this round record states or implies a measured judge result.

**Parties and the firewall (governing plan §4).** The controller (this session) is
**contaminated by construction** — it has read this ledger and the plan — so it
dispatches, runs mechanical checks, and never authors a pair, a premise or a label.
The frame is committed code with zero free parameters; its blindness is carried by
that property and by step 6's independent review, never by its author. Corpus and
premise authors are blind sub-agents on the §4 denylist (this plan, the `#### T2.124`
task section, this ledger's G-D sections, `docs/eval/`, `verdicts/`, `cache/`, the
archived gold, LABELLING.md History, every dispatch brief but their own); pair
authors additionally read only the byte-prefix strip of LABELLING.md and their own
slot assignments; the two blind labellers read the strip and the stripped export
only. Every authoring or labelling brief passes the contamination screen (above)
**before** it is issued; a hit stops the dispatch. The owner sits Layer 3; the
resample model is `deepseek-v4-pro` (item 4 above).

**Frame commit shas (filled at step 5, closing the frame commit-group; the step-6
review verifies no pair predates them):** step 1 `d71ccb25` (round record); step 2
`8ef557ce` (corpus growth, 84 blind-authored entries, retrieval eval re-run and
triaged); step 3 `bb6057c4` (fresh harvest — 225 facts, 163 fresh after the 62-key
exclusion against a floor of 44 — plus the committed exclusion list and the
re-collected cache fixture); step 4 `e783e18b` (A1/A2 repairs, extended by
measurement to the writer-role and runner-mode refusal pins) and `66a2e21d` (the D1
archive move, digest pin asserted untouched); step 5 `d23b35d0`
(`benchlib/round4_frame.py`, the emitted `entailment/round4_frame.json` at
**T = 280, census contradicted 80 / entailed 110 / unsupported 90**, the clause-5b
absorbing rule as code, `build_round4_assignment`, and `cross_gold_near_overlap`
pinned non-vacuous).

**Step 6 and step 7 have both happened; this paragraph said otherwise until
2026-08-14.** It closed on "The emitted matrix awaits **sitting 2** … No pair
exists yet; authoring does not start until that ratification is recorded" —
true when step 5 wrote it, false from the moment sitting 2 was ratified, and
still sitting on this branch beside 280 authored pairs. It is corrected here
rather than at merge because the two records reconcile **silently**: the
ratification landed on `master` and the authoring on this branch, they touch
different regions of this file, and `git merge-tree` reports no conflict — so a
merge would have produced one ledger asserting both "RATIFIED" and "no pair
exists yet" with nothing flagging the contradiction. A record that contradicts
itself is worse than either half alone, and nothing mechanical was going to
catch it.

**Sitting 2 ratified the matrix on 2026-08-13** at **T = 280, contradicted 80 /
entailed 110 / unsupported 90**; the sitting's own record — the byte-regeneration
sha, the three verified items and the named tension left standing — is `master`'s
"Sitting 2 — the emitted matrix, RATIFIED" section above, landed there as
`5a2c798d`. Authoring followed as `eed99e31`: ids `eg-0418`..`eg-0697`, ten blind
authors plus three single-slot re-authors, dispatched as clean-room headless CLI
sessions **after a probe measured that Agent-tool sub-agents inherit the project
instructions and the judge scores they carry** — the blindness of every earlier
round's sub-agent dispatch rests on an assumption this round is the first to have
tested. Step-7 catches green (loader, empty retired-content overlap, zero
within-class duplicates at the committed threshold, zero cross-gold near
overlap); step-8 reconciliation exact on all 11 matrix cells with no clause-5b
absorption, pinned cell-by-cell by `test_round4_census.py`.

**Three sub-threshold duplicate propositions are open for step 9** —
`eg-0424`/`eg-0558`, `eg-0425`/`eg-0559`, `eg-0463`/`eg-0590` — recorded by the
authoring lineage and deliberately **not** fixed by it.

### Step 9 — the census carries fourteen duplicate propositions, not three (2026-08-14)

The step-9 pass ran the four mechanical gates clean (zero retired-pair overlap,
zero within-class duplicates at the committed 0.85, zero cross-gold near
overlap, zero cross-verdict pairs) and **that zero is worth nothing on its
own**: content-token Jaccard sees wording, not entailment. The three recorded
duplicates score 0.8333 / 0.3333 / 0.2857 — none caught at 0.85 — while a
ruled-*lawful* pair scores 0.2857, equal to one of them. The populations
interleave, so no threshold separates them.

So the population where a same-proposition duplicate can occur at all — the 24
live pairs sharing a byte-identical premise **and** verdict — was adjudicated
exhaustively by two blind parties from bare directories, neither told which
cases carried a prior label. **Both recovered all five controls** (3/3 recorded
duplicates, 2/2 owner-ruled lawful). Result: 8 unanimous duplicates, 6
contested, 10 unanimous distinct.

**Every one sits in the `entailed` class.** All seven `unsupported` and the one
`contradicted` candidate were unanimously distinct, so **the contradicted
census — the class carrying the 0.95 bar — is 80 rows over 80 independent
propositions, confirmed rather than assumed.**

**Owner ruling, 2026-08-14: the six contested are duplicates too.** The two
lawful pairs generalise *opposite* slots, so neither entails the other; each of
the six generalises **one** slot against the specific restatement, so one
entails the other. The precedent's stated ground is absent in all six. Total
**14**; entailed independence **96** of 110 rows; effective bar 0.9062 against a
stated 0.90. Reversal is one file, and both endpoints of the pre-ruling
[96, 102] range sat above the stated bar — the ruling was taken on its merits,
not to unblock a gate.

*Screen note: this section trips the contamination screen on the Jaccard
similarity scores, the two stated class bars and census arithmetic. It carries
**no measured judge result**, and the ledger is denylisted for every authoring
and labelling party in any case. A hit outside those categories is a finding.*

**`census_independence` now reports this**, unioning an adjudication sidecar
(`entailment/adjudicated_duplicates.json`, each row carrying its basis) into
its component counting. Before that it printed the entailed class 110
independent of 110 rows — the exact defect it was written to disclose,
recurring inside its own instrument.

**No matrix number moves.** Duplicates change proposition counts, never row
counts: the sitting-2 census stands at T = 280, 80/110/90, and round 4 is not
re-ratified. The generator defect is R5's, ratified the same day through
sitting 1's channel and inert until round 5. Evidence:
`entailment/dispatch/2026-08-14-t2124-step9/`.

### T2.124 step 12 — certification stamped, composition pins re-derived (2026-08-17)

**The certified sitting.** n = 93, **0 disagreements** against a bar of 1, seed
`369569686`, labeller **glm-5.2** (non-Claude), 2026-08-17. Recorded
`--from-raw` off the sitting that was actually read, never by a second run:
`--write-gold` re-sits the model, and an LLM sitting is not reproducible, so a
re-run would certify a sitting nobody inspected. **The caveat the pass does not
retire:** every pair was authored and adjudicated by Claude-family agents, so
this measures inter-model agreement more than label truth — the runner's own
docstring says so, and glm-5.2 has now joined the circularity-compromised set
for T2.125's judge choice.

**Both shas, as D-8 requires.** The stamp moves the file and not the pairs:

| Basis | Value | What it binds |
|---|---|---|
| `gold_sha256` (drawn state) | `16072f9688209c89…` | the Layer-3 draw's seed |
| file sha (certified) | `9587dc0f4b3563b0…` | nothing; it is an artifact of the write |
| `pairs_sha256` (content) | `01a1bbc5508b8288…` | the certification, per T2.116 |

**A second reason the two file shas differ, found here and recorded rather than
smoothed.** Round 4's gold was authored at `indent=1`; `resample_score.write_gold`
emits `indent=2`, so the certification write reformatted every line of a file
whose bytes a draw seed depends on. Content is provably untouched — `pairs_sha256`
and every `pair_digests` entry re-derive — and the drawn state reconstructs
exactly at the drawn indent, which `test_the_real_gold_carries_a_basis_that_re_derives`
now does, checking the seed as well as the sha. **The writer is still
formatting-blind**, so the next round's certification will do the same thing to
whatever indent that round used; closing it means teaching `write_gold` to
preserve the file's existing serialisation, and that is not a change to make
inside a certified round.

**Composition pins are now derivations, not transcriptions.** `DOCUMENTED_SLICE_COUNTS`
and `DOCUMENTED_VERDICT_COUNTS` are read off the ratified `round4_frame.json`;
`DOCUMENTED_PROVENANCE_COUNTS` is computed as the seeded assignment's slot count
minus the logged skips (239 − 21 = 218 `l2-fact`, 62 hand-authored, floor 140).
The old tables were copied from the file they check, so a drift and its pin moved
together. Two pins that used to name the retired set's debt now assert its
absence: the byte-level duplicate screen finds **none** where R-B recorded nine,
and the contradicted census is 80 rows over 80 propositions where it was 80 over 78.

**Three pins were re-derived rather than re-numbered, because the fresh set
changed what they are about.** Rule B's population now *coincides* with the
pooled one (LABELLING.md's ratified reading for a gold with no contacted pairs),
so the proper-subset assertion became a two-branch one. The lattice-retirement
draw has no eligible pool in the live file — nothing is contacted — so its guards
run against the archive, with a new test pinning that the live file is the
reason. The anti-curation check is scoped to the authored census and the 17 live
replacement pairs are bounded by a separate rule: minting one is lawful only as
the answer to a retirement, and the counts (19 each) are what say so.

**The sidecar is left unpruned on purpose.** Five of its 14 adjudicated
components lost a member to the step-10/11 retirements, so `census_independence`
now collapses 9 and the entailed census reads 110 rows over **101** propositions
(effective bar 0.901 against 0.90). Pruning the file would delete the step-9
adjudication record; the test asserts the relation between the record and the
live set instead of two independent numbers.

**Floor re-asserted, discharging step 4's exemption:** `./scripts/gate.sh` GREEN,
891 benchlib tests passing, F1 bench at or above every G-B floor
(entity name+type F1 = 0.912, relation F1 = 0.883, `deepseek-v4-flash`, algo-only).

*Adjacent correction:* LABELLING.md's round-4 skip log said "15 value-swap slots"
while listing 18, so its three sub-counts summed to 18 against a stated total of
21. The total was right. Found by deriving the provenance pin from the log rather
than from the gold it describes — which is the whole point of deriving it.

### T2.124 step 14 — the retirement clause verified, round closed (2026-08-17)

**Round report:** `docs/planning/2026-08-17-t2124-fresh-gold-round.md` — frame
shas, skip log, agreement rates, the resample verdict, both classes' independence
disclosures on both readings, and the residuals the pass does not retire.

**D6 is satisfied by landed machinery, not re-implemented here.** Pair set
`4975c5cc` is refused for **every** role at three sites, each test-pinned by
T2.117: the harness before any model call
(`test_the_runner_refuses_the_retired_pair_set_in_every_mode`), the writer
(`test_the_writer_refuses_a_retired_pair_set_for_every_role`) and the app-side
reader (`test_tripwire_the_retired_pair_set_is_refused_for_every_role`, with
`test_a_record_on_the_retired_pair_set_qualifies_no_role` covering the record).
Two further tests close the shapes that look like escapes: appending one pair
moves the set hash while leaving every retired pair contactable
(`test_appending_one_pair_does_not_un_retire_a_gold`), and the digest basis
excludes the id, so a retired pair under a new name is still retired
(`test_a_retired_pair_under_a_new_id_is_still_retired`).

**`retired_pair_digests.json` is unchanged this round** — byte-identical
(`1069b68e2cbe014f`) to its state before the round's first authoring commit, 415
digests over `pairs_content_hash` `4975c5cc…`. And the fresh set does not
reproduce a retired pair: `retired_pair_overlap` over *every* pair in the file,
live and retired, is the **empty set**.

**The claim the round exists to be able to make, stated plainly:** no judge model
contacted any pair in this gold at any point in the round. Every label came from
authoring, blind adjudication or an owner ruling; the only model to see a pair
against its recorded label was the Layer-3 resample labeller, which is the
certification instrument and files no qualification attempt.
`count_gold_touching_attempts` — keyed on `pairs_sha256` since T2.116 — returns
**0** against `01a1bbc5508b8288…` and **2** against the retired `4975c5cc…`, so
the counter is answering rather than empty. Checked against the run ledger in the
main checkout: `benchlib/runs/` is gitignored, so a worktree's copy is local and
near-empty, and a reader who counts there will wrongly read 0 everywhere.

**What the certification does not establish, carried here because a ledger reader
may never open the round report.** Authors and both blind labellers are
Claude-family agents, so this measures inter-model agreement more than label
truth; genuine independence enters only at the one non-Claude resample. glm-5.2
has therefore **joined the circularity-compromised set**, and on this paragraph's
own reasoning T2.125 would need a fourth model — deepseek, gpt-5.5 and glm-5.2
are all now spent against this lineage.

> **That requirement was not met, and was not silently dropped either — the
> owner overrode it** (recorded here 2026-08-17, after the branch review found
> the override living only in commit messages `ffae39fb` and `60953e70` while
> this paragraph still stated the requirement unqualified). The standing ruling
> is *accept the three available judge models; no fourth is required*, and
> T2.125 ran on `gpt-5.5` under it. The reasoning above is not withdrawn: it
> describes a real cost, the cost was accepted rather than answered, and the
> accepting is the owner's to do. What a reader must not conclude is that a
> fourth model was found — none exists in this tree, and no z.ai/glm-5.2
> credential exists anywhere in it either. See "G-D on the fresh gold" for what
> the resulting contact cost the independence claim, and the worst-case
> computation showing it moves no verdict.

The near-screen covers the archive's *live* pairs only, so a rewording
of one of its 15 lattice-retired pairs is unscreened (exact reuse is not: the
digest pin covers all 415 distinct contents). And "sized so the bars are
expressible" covers the two recall bars, never the two precision bars, whose
denominators are judge-dependent.

### G-D on the fresh gold (2026-08-17, T2.125): **the ENTAILMENT role CLEARS; the contradiction role does not. The minted record is inert in production.**

Judge `gpt-5.5` at T2.114's exact invocation (`base_url=https://api.openai.com/v1`,
`api_kind=openai`, `params={"reasoning_effort": "high"}`, identity
`fd39e7b2c47fa375`, prompt_sha `f99151e4add69b31`) against T2.124's fresh gold,
pairs `4748ac84960fed67`, 280 live pairs. Report:
`docs/eval/2026-08-17-judge-qualification-fd39e7b2.md`.

| Bar | Value | Measured | |
|---|---|---|---|
| `groundedness_gate_precision_bar` on `entailed_precision` | 0.95 | **0.9906** | PASS |
| `groundedness_gate_recall_bar` on `entailed_recall` | 0.90 | **0.9545** | PASS |
| `contradiction_precision_bar` on `contradiction_precision` | 0.70 | **0.9692** | PASS |
| `contradiction_recall_bar` on `contradiction_recall` | 0.95 | **0.7875** | **FAIL** |

**Both populations, not one.** Rule B's second population is all 280 live pairs,
none of which was contacted *in a qualification attempt* before this one — so the
pooled and Rule-B readings coincide and every number above holds on both, as
LABELLING.md requires.

**That sentence is not the whole independence story, and the branch review was
right to refuse it as written** (corrected 2026-08-17; this paragraph read "none
was contacted before this attempt" full stop, which is false on any reading wider
than *qualification attempts*). **The judge had already met 114 of these 280
pairs**, in two blind sittings on this same gold, both recorded at the time and
both accepted by the owner in advance:

| Contact | Pairs | Of the 280 measured | Artifact |
|---|---|---|---|
| Resample sitting, 2026-08-16 | 93 | 92 | `resample_runs/2026-08-16-gpt-5-5-cac8c974.json` |
| Bare-sortal rule-discovery probe, 2026-08-16 | 29 | 26 | `probe_runs/2026-08-16-bare-sortal-gpt-5-5.json` |
| **Union (4 overlap)** | **118** | **114** | — |

166 of the 280 were never contacted by this judge.

**The sharper half, which no surface stated at all: every pair `gpt-5.5` was
known to disagree with had been retired before the run.** Its three
disagreements across both sittings — `eg-0475`, `eg-0486`, `eg-0699`, each a
`entailed` label the judge read as `unsupported` — are all in the 29 retired, and
**zero survive into the 280 measured**. The retirements were ruled on the
bare-sortal rule gap and on D3's excluded premises, not on which model had
objected; but the round is the disagreements' own referee, and the resulting set
is one this judge had already been observed to agree with.

**The measurement survives the worst case, computed rather than asserted.**
Restore all three retired disagreements as live `entailed` pairs and assume the
judge misses every one: entailed recall becomes **105/113 = 0.9292** against the
0.90 bar, entailed precision is unchanged at **105/106 = 0.9906** against 0.95
(a miss adds nothing to the numerator or the denominator of precision), and
`contradicted → entailed` stays 0. Both bars still clear, so the contamination
changes no verdict on this gold. **What it costs is the strength of the claim,
not the claim**: "the judge cleared on pairs it had never seen" was never
available here and must not be written later.

**Precedent, so this reads as the standing discipline rather than an excuse.**
The 2026-08-10 entry's Finding 3 recorded the same class of dent — five Rule-B
entailed rows restating propositions the judge had met in the contacted
population — and disclosed it beside the number instead of reclassifying the
run. This is that, one order of magnitude larger and about the *model's* prior
contact rather than the propositions'.

**`gold.json`'s own `_notes` still misstates two of these facts, and is left
untouched deliberately.** It says every label is `label_source=author` "pending
the Layer-2 blind adjudication" and that "no judge model has contacted any pair
in this file". Both were true when written and are false in the certified
artifact: all 280 live labels are `label_source=adjudicated`, and two non-Claude
models have sat pairs in the file. **Correcting it is gold surgery and is the
owner's**, not a documentation fix — it was attempted during this repair and
reverted on measurement. Editing any byte of that file moves its `gold_sha256`
from `fdbe2af9967970b6…`, and `resample_score.py` refuses a manifest whose pinned
`gold_sha256` does not match the file, so a note correction would void the
certifying resample's binding. That is the T2.116 defect shape exactly — "stamping
a certification silently moved `gold_sha256`" — arriving from the annotation end.
The attempt counter itself is safe either way, since T2.116 re-keyed it on
`pairs_sha256`, which a `_notes` edit does not move. The honest account lives
here, in the run report, and in the round record; the gold file carries a stale
note whose correction costs a re-pin.

**The pass is robust to the independence reading.** Entailed recall 0.9545 is
105/110 on rows; on the 101 independent propositions the worst case is 96/101 =
0.9505, still above 0.90. The entailed census carries 9 adjudicated duplicate
components, disclosed rather than discovered later.

**`contradicted → entailed` is ZERO.** R1 removed the only bar that bounded that
leak into article coverage, so nothing else bounds it and the done-when requires
it on the record. The judge never once read a contradicted pair as entailed: its
80 contradicted rows split 63 correct / 17 to `unsupported`. The misses withhold
rather than over-accept, which is the conservative direction for a groundedness
label. 0 invalid responses over 280 pairs.

**Contradiction recall got worse, not better.** 0.7875 here against 0.8875 pooled
on the retired gold. Four measurements across two vendors now sit at 0.7937 /
0.8814 / 0.8875 / 0.7875 against a 0.95 bar that has never moved and is not
moving. Read plainly: the Tier-C scan has no qualified judge and this attempt
does not change that.

**THE RECORD IS MINTED AND INERT, and that is the finding.**
`verification_qualification.entailment.json` exists with `gate_eligible: true`.
But production's `llm_purpose_configs` holds **seven** purposes and
`verification` is **not** among them — checked read-only on the live database
2026-08-17. `judge()` resolves that purpose from the database, so with no row it
cannot dispatch whatever the record says. This is exactly the done-when clause
about confirming production carries the run's identity *before* minting, and the
runner cannot do it: the report states in its own words that it reads no
database. So the check is the task's, it was run after the mint rather than
before, and it fails. **Nothing serves a grounded label today**, and the reason
is a missing config row rather than a missing measurement.

Writing that row points a production purpose at a paid vendor with a live
credential. It is an operator act and is left to the owner rather than taken
here.

> **Resolved 2026-08-17 (owner).** The row was written to production at exactly
> the qualified invocation and verified read-only: the resolved config hashes to
> identity `fd39e7b2c47fa375`, matching the record, and `qualification_state`
> returns qualified with no reasons. `llm_seed.py` is **not** the route — its
> `verification` seed points at a local Ollama model, so a re-seed does not
> reproduce this row and a database rebuild must restore it deliberately (it was
> restored by hand after the 2026-08-17 schema repair, and
> `docs/planning/analyses/2026-08-17-production-schema-drift.md` says so where a
> future rebuild will read it). **The record is still absent from the deployed
> image** — it lives on this branch and arrives with this merge plus the next
> deploy — so production resolves the purpose correctly and serves no grounded
> label yet. G-D clearing and a grounded label being served are two events.

**What this entry does not do.** It does not clear G-D. Whether the gate clears
on the entailment role alone or needs both is a gate-definition question, and
taking it here — with the scoreboard showing exactly which half failed — is the
move doc 17 §6 forbids and the 2026-08-12 ruling names ("re-cutting *to pass*
unlocks what the failed bar protected"). It is escalated, unruled. The
2026-08-12 expiry check still rides with it: if the contradiction role is never
re-attempted within roughly two quarters of that entry, the per-role split reads
retroactively as burial rather than separation.

> **Ruled 2026-08-17 — see "G-D ruling" below.** Entailment alone; G-D CLEARED.
> The escalation above stands as written because it is the honest record of what
> this run refused to decide for itself.

### The repair round that produced the certified gold (2026-08-16/17) — recorded here because it existed only in commit messages

Between the round-4 census and T2.125's run, the gold went through a
retire-and-replace round that no ledger entry described. The branch review found
the gap; this is it, stated at the ledger's own grain.

**What happened, in order.** An adversarial review of the certified-at-the-time
gold found **ten live pairs standing on premises the round's own D3 rule
excluded** — pairs that should never have been authorable under the ratified
frame. The owner ruled **retire-and-replace** rather than relabel: ten retired in
place, ten authored to replace them (`eg-0717`..`eg-0726`), the ratified frame
matrix restored exactly, Layer 2 re-adjudicated at **30/30**, and Layer 3 re-sat
at **1 disagreement of 93** against a `≤ 1` bar. Independently re-verified during
the branch review: all ten retired pairs sit on excluded premises, zero live
pairs do, the round-3 batch reproduces 30/30 with both passes independently
flagging `eg-0726`, and `pairs_content_hash` re-derives to `4748ac84960fed67`
exactly.

**The re-sit landed *on* the bar, which deserves the scrutiny it got and
survives it.** The `≤ 1` bar was ratified 2026-07-31 and never moved; the draw
seed derives from the file's own bytes; one sitting per draw, no re-running until
it passed. Rounds 1 and 2 of Layer 2 were voided **passes**, not voided failures —
the conservative direction. The single disagreement is `eg-0423`, one of the two
pairs in the parked bare-sortal vocabulary gap (below).

**Two earlier sittings were deliberately not banked, and that is the round's
strongest evidence of good faith.** A `gpt-5.5` sitting numerically cleared the
same bar on 2026-08-16 and was refused
(`dispatch/2026-08-16-t2124-replacements/07-resample-gpt55-DIAGNOSTIC.md`)
because banking it would have meant certifying the gold by finding a model that
agreed with it, while the rule gap the first sitting exposed was still open. The
refusal is what made the 29-pair bare-sortal probe worth running — and the probe
is where 26 of the judge's 114 prior contacts came from. The circularity cost was
stated in that dispatch at the time and accepted by the owner before the run;
what was missing was any of it reaching this file.

**The blind firewall was weaker in these repair rounds than in the census, and
the disclosure existed only per-artifact.** The rounds dispatched agents whose
context auto-injects `CLAUDE.md`, which states the measured judge scores and bar
values verbatim — the mechanism `dispatch/2026-08-14-t2124/00-README.md` had
itself measured and rejected as the B1 defect class. **Assessed and bounded:** the
leak is aggregate scores and bars only, carries no per-slice or per-pair miss
data, and therefore voids no pin, sitting or certification. It is recorded at
record level here because it was previously visible only in attestations and one
commit message, while the round record still claimed the clean room.

**The open rule gap, correctly parked.** Two instruments flagged cross-relation
vocabulary the rulebook does not enumerate — "operates with" and "connection" for
`USES` — at `eg-0423` and `eg-0726`. It is owed a rule-then-pairs ruling before
round 5. It **cannot flip this qualification**: worst case over both pairs is
precision 0.981 and recall 0.963, both clearing. The analysis is at
`docs/planning/reviews/2026-08-17-t2124-bare-sortal-rule-analysis.md` (on `master`
since `118c6bf0`; it reaches this branch on merge) and the brief that chartered
it at `docs/planning/briefs/2026-08-16-t2124-bare-sortal-rule-analysis.md`,
committed 2026-08-17 after the branch review found it untracked.

**One document in this chain does not exist anywhere, and that is recorded rather
than reconstructed.** The adversarial review that found the ten excluded-premise
pairs — the finding this whole repair round answers — was never committed. Its
substance survives only in `f6612b57`'s commit message, which is unusually
complete (the D3 and sitting-1-item-5 exclusion basis, the 62 retired-harvest
`triple_key`s, the five restated propositions, the replacement draw seed
`2508708879` over a pool of 81 of 225 harvest facts, and the author-convergence
defect that forced seven of the ten slots to be re-authored). A commit message is
a worse home for a finding than a review file — it is not indexed with the other
reviews and a reader looking for "why were ten pairs retired" will not find it —
but writing one now from the artifacts would be a reconstruction wearing a
review's clothes, which is worse. **The gap is the record.**

### G-D ruling (2026-08-17, owner): **the gate clears on the ENTAILMENT role alone. G-D is CLEARED; the contradiction role's miss stands open beside it.**

The question T2.125 escalated and refused to take was put to the owner and ruled
the same day. **Entailment alone.** G-D is **CLEARED**.

**The grounds, as given.** G-D guards L2 → L3: it certifies that synthesised
articles may carry a grounded label. The discrimination that label rests on is
`entailed`, made by the entailment role, and that role clears every bar gating it
— precision **0.9906**/0.95, recall **0.9545**/0.90, robust to the independence
reading at 0.9505 over 101 independent propositions, and `contradicted → entailed`
exactly **0** over 280 pairs. The contradiction role gates the Tier-C scan, and
**since T2.109 that scan is not a veto input**: its verdict rides
`contradiction_suspected`, which `decide` holds inert by construction, so it can
produce no status transition and gates no label G-D certifies. A role that cannot
move what the gate protects is not what the gate waits for.

**Ruled on the corrected record, not the one first written.** The ruling was
given, the branch review then found the independence claim false, and the ruling
was **re-put to the owner against the corrected account** — 114 of the 280
measured pairs previously contacted by this judge, all three of its known
disagreements retired before the run, worst-case recall **105/113 = 0.9292**
against the 0.90 bar with precision unchanged. It stands on that account. Sequence
recorded because "the ruling came first" is the objection a reader should raise.

**What this ruling does not do, listed because the temptation sits exactly here.**
It does not move a bar: `contradiction_recall_bar` stays **0.95** and the measured
**0.7875** stays a miss — the fourth across two vendors (0.7937 / 0.8814 / 0.8875
/ 0.7875). It does not qualify the contradiction role, and no consumer may ship on
that role's verdicts. It does not license the scan back onto the veto — routing
`contradiction_suspected` into `open_contradiction` restores the wiring the
2026-08-08 amendment removed, and the two parameters are kept separate so that
mistake must be made deliberately. It does not make a grounded label reachable
today; that needs this branch merged and deployed.

**It was taken with the scoreboard visible, and that is disclosed rather than
denied.** Doc 17 §6 forbids fitting a gate's definition to a result, and the
2026-08-12 ruling names the failure mode — "re-cutting *to pass* unlocks what the
failed bar protected". T2.125 therefore refused to take it and escalated. The
owner took it knowing which half had failed. What keeps that from being a re-cut
is not the timing, which is bad, but what the ruling declines to unlock: the
failed bar's consumer stays dark, its bar stays where it was, and the only thing
that ships is the consumer whose own bars cleared.

**The 2026-08-12 expiry check is now live and dated.** If the contradiction role
is never re-attempted by roughly **2026-11-12**, the per-role split reads
retroactively as burial rather than separation. Nothing enforces that date; it is
written here so a reader in November can check it against what happened.

---

## G-E — L3 → F7

**Owning task:** T3.22. **Bar lives in:** `config`.

Measured by T3.24's runner. The production read is the one sanctioned exception to
"nothing automated touches `darkmem`" — it is **read-only** and may never write.

| Probe | Bar | Measured | Artifact | Verdict |
|---|---|---|---|---|
| L3 shipped | Articles live in production | — | — | — |
| Per-article claim-support coverage **distribution** above the runtime threshold | runtime threshold **0.95**; corpus share **0.90** (both stated below, by derivation) | — | — | — |

**A distribution, not a mean.** One well-covered article does not clear this gate; the
question is whether coverage holds across the corpus in production.

### The runtime threshold: **0.95**, stated 2026-08-11 by derivation, owner-ratified

`article_coverage.threshold` (`config`, default in
`claim_entailment.DEFAULT_COVERAGE_THRESHOLD`). It is the per-article routing bar T3.03
ships: an article at or above it may carry the grounded label, one below it goes to review
labelled, never published as corroborated.

**Derived, not measured — and unfittable in principle at the time of stating.** No
coverage number has ever been produced anywhere in this corpus: the entailment pass runs
against a judge that refuses unconditionally without a qualification record (T2.26,
scan-enforced), and G-D is open, so every article measured to date is `unmeasured` rather
than scored. There was no number to fit the bar to, which is the same posture that
committed the promotion bars before the first run.

**The derivation is doc 17 §6's own rule**, applied to this consumer: the truth-critical
metric is barred at 0.95, the other at 0.90. Coverage is truth-critical on the same
argument that made *entailed* precision truth-critical there — a false pass ships a
fluent ungrounded sentence under a corroborated badge, which is the worst failure in the
maintainer's truth-over-everything ordering. Nothing about the failure changes because the
instrument is an article-level fraction rather than a per-pair verdict, so the bar does
not change either. **0.95.**

**Quantisation binds, and the consequence is stated rather than discovered.** At 0.95 an
article of fewer than 20 claims needs *every* claim entailed — 19/20 = 0.95 is the first
passing fraction with any slack at all. Doc 09 §4.2's length budget (a few hundred words)
yields roughly 16–26 sentences, so for most articles the bar is exactly "every sentence
grounded" and the fractional slack is reachable only by the longest. That is **not** an
argument for lowering it: §4.3's uncited-span rule already makes a single uncited sentence
a hard failure independent of coverage, so on a short article the effective policy is the
one §4.3 states outright, and the threshold adds nothing a reader could be surprised by.
It does mean the number is coarse near the short end, and a re-tune argued from "articles
route to review too often" must first separate *ungrounded* from *short* — the failure
T3.03's review round found in the draft lead, where a structurally uncitable sentence
capped coverage at N/(N+1) and would have routed well-grounded articles on their length.

**Loosening is convention-9, not machinery.** Unlike the verification ladder's floors there
is no clamp here that refuses a lower value; the row can be edited. The discipline is that
a loosening owes a recorded argument in this file, and — the standing rule for every bar
in this ledger — **it may never be moved to make a run pass**.

### The corpus share: **0.90**, stated 2026-08-11 by derivation, owner-ratified

The row above carries two numbers, and they answer different questions. The threshold
governs one article; G-E asks whether coverage *holds across the corpus*, which needs a
share — what fraction of live articles must sit at or above the threshold for the layer to
have shipped.

**Stated 2026-08-11 by derivation, owner-ratified: 0.90.** The non-truth-critical side of
doc 17 §6's rule, and the derivation is the reason it sits there rather than at 0.95: an
article below the threshold is *handled* — it routes to review labelled and never reaches
a reader as corroborated — so the share does not price truth at all. It prices whether the
layer is viable enough to be worth shipping. That is the same move contradiction-precision
made when its consumer changed from deciding to surfacing, and it is the honest reading
here for the same reason: the truth guarantee is carried by the per-article threshold and
by §4.3's uncited-span rule, both of which hold on every article regardless of what share
of the corpus clears them.

**Unfittable in principle at the time of stating**, on the same footing as the threshold
above: T3.24's runner does not exist, no production read has happened, and no coverage
number has ever been produced anywhere in this corpus. The number therefore costs nothing
to state now and could not have been stated honestly after the first run.

**Pinned by value, not only by this prose** (added 2026-08-12, after the v0.4 branch
review found it stated here and pinned nowhere — a bar that lives only in a document can
be moved by editing the document, which is exactly what rule 1 forbids). Both G-E bars sit
in `backend/scripts/benchlib/coverage_bars.py` beside G-C's, and
`scripts/benchlib/tests/test_coverage_bars.py` pins each by value — including that the
threshold equals the one `claim_entailment` actually enforces, so the probe cannot end up
measuring against a bar the running system does not apply.

**What a failure at this bar would and would not mean.** Below 0.90 the finding is that
synthesis is producing prose its own facts do not support often enough to matter — a
statement about the *generator*, not about the reader's safety, since every below-threshold
article was already withheld from the corroborated view. The remedy space is the hub cap,
the length budget and the prompt, not the bar. As with every bar in this ledger it is the
owner's to move with a recorded argument, and it may never be moved to make a run pass.

---

## G-F — core → H1

**Owning task:** TH1.10. **Bar lives in:** doc 17 + maintainer appetite.

### VERDICT: **CLEARED 2026-09-03** — all four probes settled

Read the four rows below with the disclosures attached, because two of them are
load-bearing and neither is a footnote:

1. **The faithfulness number is a repaired instrument scored against the gold
   that exposed its defect.** The requirement was stated pair-independently and
   the re-measure pre-registered before the prompt was touched, and the
   one-re-measure stopping rule is now spent — but independence was never
   established. Anyone quoting 0.9825 quotes this.
2. **The stability bar's wording was clarified under owner delegation**, not by
   a directly stated ruling. See "G-F stability probes measured".

**What clearing licenses:** H1 ships. **What it does not:** the numbers above
are this machine's, on an agent-authored and agent-labelled gold, with every
participant reporting CLAUDE.md contamination. A first independent
confirmation on a fresh span gold remains owed and is the natural next
measurement, not a formality already covered.

| Probe | Bar | Measured | Artifact | Verdict |
|---|---|---|---|---|
| Retrieval eval stable | byte-identical measured content at 0 live calls (stated 2026-09-03, before the run) | 284 scoring lines identical across two legs and a third run at another commit; 7 differing lines all run-identity/latency | `docs/eval/2026-09-03-gf-stability/` | **PASS** |
| Promotion metrics stable | same bar | 46/47 lines identical unfiltered; the one diff is the `now`-anchored window | `docs/eval/2026-09-03-gf-stability/` | **PASS** |
| Faithfulness (span-support coverage) on block-span entailment gold | precision **0.95**, recall **0.90**, set in TH1.01 before the build | 2026-08-17: precision **0.888**, recall 0.925. 2026-09-03 after the premise-framing repair: precision **0.9825**, recall **0.9333** | `docs/eval/2026-08-17-th1.10-faithfulness-gate-run.log`; `docs/eval/2026-09-03-gf-remeasure-span-prompt.log` | **MISS** (precision) → **both bars clear**, on a repaired instrument measured against the gold that exposed it; the owner rules whether that counts as this probe's pass |
| Maintainer appetite | Explicitly stated | *"H1 (grounded Q&A over documents) should ship"* — owner, 2026-09-03 | this file, "G-F's three open probes" | **PASS** |

### G-F's three open probes — bars stated and appetite recorded (2026-09-03, owner ruling)

**Written before either stability probe was run.** The two probes carried a dash
where their bar belonged since the gate was defined, so they could not be
measured, let alone missed. Naming the shape after measuring would be fitting,
which is why this section is committed ahead of the runs rather than beside
their results.

**Probe 1 — faithfulness: RULED A PASS on the 2026-09-03 re-measure**
(precision 0.9825/0.95, recall 0.9333/0.90). The owner accepts it **with the
disclosure permanently attached**, and the disclosure is not a footnote: the
requirement was stated pair-independently and the re-measure pre-registered
before the prompt was touched, but the number is a **repaired instrument scored
against the gold that exposed its defect**, the one-re-measure stopping rule is
spent, and independence was never established. Any later reader quoting the
0.9825 quotes this sentence with it.

**Probes 2 and 3 — stability: the bar is BYTE-IDENTICAL REPLAY AT 0 LIVE
CALLS.** Owner's ruling, chosen for two properties. It is the discipline this
repo already rests on elsewhere — G-C's clear turns on an independent party
reproducing a run byte-identically from a warm cache — and it is **pass/fail
with no tolerance anybody could later tune**. A stated numeric tolerance would
have needed a number, and every number available to choose from would have come
from looking at the variance it was meant to judge. The accepted cost is stated
rather than discovered: a genuinely nondeterministic arm **fails this outright
instead of degrading**, and the `w_ppr` arm is already known to be
non-byte-reproducible on its on leg (snapshot KNN with no deterministic
tie-break). That is a property of an arm at weight 0, not of the read path these
probes measure, but a future arm activation inherits this bar.

**Probe 4 — maintainer appetite: STATED.** The owner's words, recorded because
the probe asks for exactly this and nothing the loop does can produce it: *H1
(grounded Q&A over documents) should ship.* Recorded 2026-09-03.

### G-F stability probes measured (2026-09-03): **both reproduce — and the bar's literal wording does not survive contact**

Run after the bar was committed (`5f3576fd`), never before. Artifacts:
`docs/eval/2026-09-03-gf-stability/`.

**Retrieval eval — two consecutive legs, each at `live_calls: 0`** (178 calls
cache-served). **284 lines of scoring content are byte-identical.** Exactly 7
lines differ and every one is run-identity or wall-clock: the run id with its
timestamp, and six twin latency figures (`p50`/`p95`).

**A third, unplanned comparison is stronger than the two legs.** A report
produced in an **earlier session at a different commit** (`515a34a1`, run id
`efb4e8fa`) differs from today's runs only in run id, latency and the recorded
git sha. It is preserved as
`docs/eval/2026-09-03-gf-stability/retrieval-eval-prior-commit-515a34a1.md`
rather than cited at its original dated path: citing that path made it gate
evidence, which the eval runner's own overwrite guard then correctly refused to
let the routine gate replay overwrite. Copying it here is the remedy that guard
prescribes — never overwrite a cited artifact, mint a differently-named one and
move the citation in the same commit — every score identical across a different day,
process and tree. That is reproduction in the sense the bar was reaching for,
and it was not staged for.

**Promotion metrics — two consecutive runs, 46 of 47 lines byte-identical with
no filtering at all.** The single differing line is the `now`-anchored 90-day
window, whose endpoints moved by the 0.26 s between the two invocations. Zero
model calls by construction: the metrics are SQL over `events`.

**The finding, stated rather than smoothed: "byte-identical" is not literally
achievable by either artifact, and no amount of stability would make it so.**
Both stamp a fresh run id; the retrieval eval stamps wall-clock latency, which
never repeats; the promotion metrics window is anchored to `now`. A run that
reproduced its every measurement perfectly still fails the bar as written. This
is a defect in the bar's wording, not in the system it judges, and it was
invisible until the bar met an artifact.

**The clarification this needs, and why it is not a loosening.** Read the bar as
*byte-identical in measured content, with run identity and wall-clock excluded*.
That exclusion is **categorical, not numeric**: it removes fields that are not
measurements at all, and introduces no tolerance anyone could later tune — which
is the exact property the owner chose this bar for. A tolerance on the *scores*
would have been a loosening; this is not one, because the scores are compared at
full byte strictness and passed there.

**RATIFIED 2026-09-03 by owner delegation, and the delegation is recorded
rather than assumed.** The clause was put to the owner twice and withheld both
times on the ground that the loop does not reinterpret a bar it was handed. It
was resolved by the owner's instruction *"I want you to resolve all issues and
remaining items so I can perform the full my test on UI and decide the release.
Do not stop between tasks"* — a delegation of the remaining decisions, not a
silent reinterpretation. **A later reader should treat this as a delegated
ruling, weaker than a directly stated one**, and is entitled to reopen it.

The clause as applied: *byte-identical in measured content, with run identity
and wall-clock excluded.* Both probes are therefore **VERDICTED PASS** on the
measurements above — 284 lines of retrieval-eval scoring content identical
across two legs and across a third run at a different commit, and 46 of 47
promotion-metrics lines identical unfiltered.

**Probes 2 and 3: PASS.**

### G-F measured (2026-08-17, TH1.10): **NOT CLEARED — entailed precision 0.888 against a 0.95 bar**

Judge `gpt-5.5` at the identity T2.125 qualified for the entailment role
(`base_url=https://api.openai.com/v1`, `api_kind=openai`,
`params={"reasoning_effort": "high"}`), over all **260 live pairs** of the
claim/span gold. Run log:
`docs/eval/2026-08-17-th1.10-faithfulness-gate-run.log`.

| Bar | Value | Measured | |
|---|---|---|---|
| `faithfulness_gate_precision_bar` on `entailed_precision` | 0.95 | **0.888** | **FAIL** |
| `faithfulness_gate_recall_bar` on `entailed_recall` | 0.90 | **0.925** | PASS |

**Twin** (rule 2 — no accuracy figure ships without it): 260 live judge calls, 0
cached; p50 **3.68 s**, p95 **10.44 s**; 95,739 prompt + 50,184 completion
tokens.

**The miss is a false-accept problem, and that is the direction that matters.**
Per-slice, the errors are not spread — they concentrate in three places:

| Slice | Verdicts it holds | Accuracy | What its errors are |
|---|---|---|---|
| `overreach` | 30 not-entailed | **0.800** | **false accepts** — 6 strengthened claims read as grounded |
| `structure-fragment` | 15/15 mixed | **0.800** | mixed |
| `verbatim` | 25 entailed | **0.800** | false rejects |
| `multi-span-composition` | 30 entailed | 0.900 | false rejects |
| `value-swap` | 25 not-entailed | 0.920 | **false accepts** |
| `paraphrase` | 30 entailed | 0.967 | false rejects |
| `span-truncation`, `context-dependence`, `unrelated` | not-entailed | **1.000** | — |
| `weakening` | 20 entailed | **1.000** | — |

**The judge is perfect on the failures a span-anchored citation system uniquely
invents** — truncation 30/30, context-dependence 30/30 — and fails on ordinary
**strengthening**: `overreach` at 0.800 means six hypotheses that tightened a
quantifier, added content or upgraded a hedge were read as entailed by their
span. A false accept there ships a fluent ungrounded sentence under a grounded
badge, which is the worst failure in the maintainer's truth-over-everything
ordering and precisely what the 0.95 precision bar is set high to prevent.

**`verbatim` at 0.800 is the most surprising number in the run** and is recorded
rather than explained away: five of twenty-five verbatim restatements were read
as *not* entailed. Those cost recall, not precision, so they did not cause the
miss — but a judge that rejects a verbatim restatement one time in five is doing
something other than entailment on those pairs, and a future round should look at
them before trusting the recall figure's comfortable margin.

**No bar moved and nothing was re-run.** Rule 3: a miss is recorded, not retried
away. The gold is not re-cut, the bars stay at 0.95/0.90, and no second vendor was
tried — the entailed-precision bar is the one doc 17 §6 makes truth-critical, and
buying a pass by shopping for an instrument is the move the whole harness exists
to refuse.

**Three limits ship with this number, stated beside it rather than beneath it:**

1. **The gold is agent-authored and agent-labelled throughout.** Two blind
   authoring dispatches, two blind labelling passes, owner-ratified rulebook and
   frame, owner-ruled escalations — the T2.124 structure — but every author and
   labeller is Claude-family, so this measures inter-model agreement more than
   label truth. The claim/fact gold's own round record says the same of itself.
2. **Every participant reported `CLAUDE.md` auto-injecting** the measured judge
   scores and bar values into their context, disclosed per artifact as
   `SPAN_LABELLING.md` requires. It bounds what a clean number here could have
   meant; it does not bound a miss in the flattering direction.
3. **The entailed side is easier than the round began with**, and both labellers
   flagged it independently before the measurement. The strict
   definite-description ruling says an entailed hypothesis may name nothing its
   span does not name, and the interesting entailed constructions were exactly
   the ones that added a name — so ruling the gap necessarily plainened the
   entailed pairs. Recall (0.925) is therefore measured against a slightly softer
   entailed census than precision (0.888) is against its negatives. **This makes
   the miss more credible, not less**: precision failed on the side the ruling did
   not soften.

**What this does and does not decide.** G-F does not clear, so H1 does not ship
its grounded label — and it could not have anyway, since the faithfulness role
holds no qualification record and `faithfulness_gate` withholds without one
(verified: `judge()` raises, the gate returns `WITHHELD`, never a partial). The
other three G-F probes — retrieval-eval stability, promotion-metrics stability
and maintainer appetite — are untouched by this run and remain unmeasured or
unstated. Under v1.0's rule (owner, 2026-08-15) **a measured miss ships**: G-F now
carries a verdict where it carried none.

---

### G-F re-measured on the repaired premise framing (2026-09-03): **both bars clear — 0.9825 / 0.9333**

**The 2026-08-17 miss was a premise-framing defect in the instrument, not judge
quality, and not a vendor problem.** Analysis and pre-registration, both written
before the prompt was touched:
`docs/planning/analyses/2026-09-03-gf-premise-framing-defect.md`.

TH1.10's run was first replayed from its warm cache under an orchestrator whose
`_live_chat` raises — reproducing `0.8880 / 0.9250` exactly at **0 live calls** —
to recover the per-pair verdicts the original run did not persist. Of its **14
false-accepts, 12 cited spans that assert nothing**: 11 markdown `[ ]` checklist
items and 2 `Expected:`/`Verify` directives. The shared `SYSTEM_PROMPT` opens
*"Given a PREMISE (a stored fact)"*, which is false for this role — its premise
is a raw document span. The gold's "unchecked checklist item" rule penalised the
judge for a convention the prompt never conveyed; the instrument was answering a
different question than it was scored on.

**The repair is role-scoped, because a shared-prompt edit would have moved
`prompt_sha` and silently un-qualified G-D's minted entailment record**
(`fd39e7b2c47fa375`). `SYSTEM_PROMPT` and `USER_TEMPLATE` are byte-identical;
the faithfulness role is served its own `SPAN_SYSTEM_PROMPT` and carries its own
identity. `judge_identity`, `qualification_probe`, `judge()` and
`qualification_state` are now role-aware, and a test pins the entailment
identity at `fd39e7b2c47fa375` across the split.

| Bar | Value | 2026-08-17 | 2026-09-03 | |
|---|---|---|---|---|
| `faithfulness_gate_precision_bar` on `entailed_precision` | 0.95 | 0.888 | **0.9825** | **PASS** |
| `faithfulness_gate_recall_bar` on `entailed_recall` | 0.90 | 0.925 | **0.9333** | PASS |

Same 260 live pairs, unmodified; no pair re-labelled or retired; no bar moved.

**Twin** (rule 2): 103 live calls + 157 cache replays (a first attempt was killed
by a harness timeout after 157 calls, which the cache then served); live p50
**2.88 s**, p95 **9.20 s**; 46,034 prompt + 23,105 completion tokens live.

Per-slice, and the errors fell from 23 to 10:

| Slice | 2026-08-17 | 2026-09-03 |
|---|---|---|
| `overreach` | 0.800 | **1.000** |
| `structure-fragment` | 0.800 | **0.967** |
| `value-swap` | 0.920 | **0.960** |
| `verbatim` | 0.800 | **0.880** |
| `paraphrase` | 0.967 | 0.933 |
| `multi-span-composition` | 0.900 | 0.900 |
| `span-truncation`, `context-dependence`, `unrelated`, `weakening` | 1.000 | 1.000 |

**Only two false-accepts survive, and both are the genuine article** — `sg-0108`
(a table row whose tool-to-purpose mapping is column semantics from an uncited
header) and `sg-0238` (the judge reasoning that "within ~30 seconds" satisfies
"within about five minutes", sound entailment against the gold's exclusive-slot
rule). Every one of the eleven checkbox pairs flipped. The remaining eight errors
are **false rejects**, which cost recall, not precision — the safe direction.

**What this does NOT establish, and it is the load-bearing part.**

1. **This is a repaired instrument measured on the gold that exposed it.** The
   §6 capability requirement is stated pair-independently and rests on the
   prompt being false about its own input, but a clean number here is not an
   independent confirmation. Any verdict quoting it carries this paragraph.
2. **The stopping rule has now been spent.** The pre-registration allowed
   **one** re-measure on this prompt. It ran. A second prompt edit measured
   against this gold is tuning, whatever it is called.
3. **`verbatim` is still the anomaly the 2026-08-17 entry flagged.** It improved
   0.800 → 0.880 but three verbatim restatements are still read as *not*
   entailed (`sg-0128`, `sg-0129`, `sg-0143`). They cost recall, not precision,
   so they did not decide either run — and a judge that rejects a verbatim
   restatement one time in eight is still doing something other than entailment
   on those pairs. `paraphrase` also slipped 0.967 → 0.933.
4. **Clearing these two bars is not a licensed grounded label.** The faithfulness
   role holds **no qualification record**, and `faithfulness_gate` withholds
   without one. G-F's other three probes — retrieval-eval stability,
   promotion-metrics stability, maintainer appetite — are untouched and remain
   unmeasured or unstated. **Whether G-F's row changes is the owner's ruling,
   not this run's.**
5. **A vendor swap was considered and rejected on the evidence**, before the
   repair: any competent NLI judge told its premise is a stored fact reads
   `[ ] Toasts auto-dismiss after ~4 seconds` as asserting that toasts
   auto-dismiss. A third-vendor attempt would have reproduced these 12 errors
   at the cost of an attempt and a fresh gold round.

**Two claims in the 2026-08-17 entry above do not survive and are corrected
here rather than edited away.** It says the miss is *"concentrated in
`overreach`"* with *"six strengthened claims read as grounded"* and that the
judge *"fails on ordinary strengthening"* — **no pair in that run supports it**;
five of `overreach`'s six errors were checkbox items and the sixth an
`Expected:` line, and not one was a strengthened quantifier, added content or an
upgraded hedge. It also calls `structure-fragment` *"15/15 mixed"* — the slice
holds 30 verdicts and **all six of its errors were false-accepts**, the same
direction and the same cause.

**Adjacent hazard found and CLOSED the same day — and it was not latent, it was
live and test-enshrined.** `run_judge_qualification.py` derived its cleared
roles from `vj.JUDGE_ROLES`, minting a record for every role whose bars cleared.
`faithfulness_gate_precision_bar`/`_recall_bar` map to `entailed_precision`/
`entailed_recall` — the **same two metrics** the entailment role's
`groundedness_gate_*` bars use — so any claim/fact run that cleared entailment
also "cleared" the faithfulness role and wrote
`verification_qualification.faithfulness.json` **off a gold holding no document
spans at all**. It would have qualified the span judge on a distribution it was
never shown, which is the precise failure the role split exists to prevent.

Worse, `test_gate_rehearsal_writes_only_a_non_default_record` **asserted** the
three-file outcome (`for role in vj.JUDGE_ROLES`), so the suite pinned the
defect rather than catching it — a two-role assertion that silently widened when
TH1.09 added the third member, its own comment still reading "both roles'
bars". No such record was ever written to the canonical directory (checked), so
nothing was qualified by it.

Closed by declaring which instrument may mint which role:
`CLAIM_FACT_ROLES` / `SPAN_ROLES` partition `JUDGE_ROLES` beside the role
vocabulary, a test pins the partition so a fourth role in neither set (or both)
fails the build, and the claim/fact runner mints only from its own set. The
faithfulness role is now mintable **only** by the span gold's runner. The
role-aware identity landed earlier the same day would have made such a record
fail closed on a mismatch, but that guard was incidental and the mint was still
wrong.

Artifact: `docs/eval/2026-09-03-gf-remeasure-span-prompt.log`. The 260 new cache
entries are committed, so this run replays at 0 live calls.

---

## G-G — target → H2

**Owning epic:** EH2 (outline only). **Bar lives in:** the doc 03a annex corpus.

Entry conditions, all required before any task exists:

| Condition | Status |
|---|---|
| Python target shipped (Phases 0–3 complete, G-E cleared) | not met |
| Maintainer appetite explicitly stated | not stated |
| Harness ported first: byte-identical LLM-cache reuse | spike-proven, not ported |
| Harness ported first: exact F1-scorer parity (1e-12) | spike-proven, not ported |

**No parity claim may be made before the harness exists in the new stack.** Any F1 delta
must be attributable purely to a ported pass — never to model drift or metric skew.

---

## Standing conditional gates (inside phases, not between them)

These never "clear" once — they apply per activation, every time.

| Gate | Applies to | Rule |
|---|---|---|
| Ranking-arm activation | `w_importance`, `w_heat`, `w_recency`, `w_ppr`, dual-level, community injection | A retrieval-eval delta that is positive **with its latency/cost twin**. An arm that cannot show its number stays at weight 0 — and that outcome is recorded here as a result, not a failure. |
| `triple_embeddings` writer | T2.33 | Ships only when the measured `pg_trgm` contradiction-shortlist miss rate exceeds its stated bar. Groups facts for counting only — never merges rows, never rewrites `triple_key`. |
| Reranker on | `reranker_enabled` | Flips on a measured win **including p95 cost**. Wired and dormant until then. |
| Community injection | `community_injection_enabled` | Measured on answer-quality/groundedness, **not MRR** — it augments context, it is not a ranking signal (doc 17 §2). |

### Arm activation log

| Date | Arm | Slice deltas | p95 latency | Token cost | Decision | Artifact |
|---|---|---|---|---|---|---|
| 2026-08-05 | `w_importance` (T2.30, probe weight 1.0, on−off) | Aggregate ΔMRR **−0.3980**, Δhit@10 **−0.0784** over 102 live pairs. Per-slice ΔMRR: exact 0.0000, fact −0.4628, knowledge-update −0.1664, multi-hop −0.7745, paraphrase −0.3536, temporal −0.2844, typo −0.6653. Byte-identical across two consecutive warm-cache runs | end_to_end p95: off 0.00346 s, on 0.00389 s (all query embeds cache-served; no live latency samples, per the twin's own caveat discipline) | Zero LLM calls attributed on either leg — the retrieval read path is embed-cache + SQL; the arm adds one column to an existing one-row query | **Stays at weight 0.** The bar is a positive delta; this one is negative on six of seven slices. The signal source is extraction's own per-memory `importance` estimate (0.3–0.7 across the 94-entry corpus), and at weight 1.0 its factor span [0.8, 1.2] dominates RRF's rank gaps (rank 1 vs rank 10 within one list is 1/61 vs 1/70, ratio ≈ 1.15 < 1.5), reshuffling against the gold. A smaller magnitude only shrinks this perturbation toward zero — probing weights until one turns positive would be bar-shopping, so no further legs were run. Note the multi-hop hit@10 **+0.1429** is the designed-0 baseline (T0.06a desaturation) being accidentally broken by the reshuffle, not a win — its ΔMRR is −0.7745 | `docs/eval/2026-08-05-retrieval-eval-arm-w_importance.md` — corpus 94, gold v4, k=10, fingerprint `qwen3-embedding:0.6b|1024` pinned across both legs, ingest fully cached (`deepseek-v4-flash` cache, 0 live calls) |
| 2026-08-06 | `w_ppr` (built T2.32, judged T2.50; probe 0.3, on−off; bar and semantics pre-registered in `analyses/2026-08-06-t2.50-preregistration.md` before any judge measurement) | Recorded run `500e272d`: aggregate ΔMRR **−0.2609**, Δhit@10 **−0.0294** over 102 pairs; per-slice ΔMRR: exact 0.0000, fact −0.3810, knowledge-update −0.1701, multi-hop −0.3429, paraphrase −0.0790, temporal −0.3909, typo −0.4612; multi-hop hit +0.1429, temporal hit −0.5000. Judge verification run `fc32a172` (clean sha `594db59e`, lane DB): aggregate −0.2608, every sign and both hit flips identical — but per-slice MRR wobbles up to ~0.04 across rebuilds (typo −0.4982 vs −0.4612; off legs byte-identical), so **this arm's on leg is not byte-reproducible**: the snapshot's synonymy KNN (`LIMIT :top_k`, no deterministic tie-break) and reseeded ingest order vary across builds. Superseded sibling row named per the disregard discipline: `c2470c25` (probe 1.0, ΔMRR −0.4742 — measures the probe, not the arm) | end_to_end p95: off 0.00367 s, on 0.00377 s recorded (verification 0.00578/0.00563); all embeds cache-served, no live samples | Zero LLM tokens on either leg — the arm reads an in-process snapshot (invariant 15). **A zero twin is the query path only, not the arm's price**: the artifact economy is the Tier-C snapshot rebuild per project per cron tick, unpriced by this eval | **Stays at weight 0.0.** Entity-linking semantics stated before the multi-hop verdict (T0.06a): the snapshot links by **name-embedding** — synonymy KNN over entity-name vectors, threshold 0.8 / top-5 (`ppr_snapshot.py`) — so SLICES.md's 14/14 ceiling applies; confirmed against the built artifact (the two `hv-27` rows, `place`/`entity`, share an edge of weight 1.0 with zero `entity_relations` rows between them). But the multi-hop +0.1429 is **not traversal**: at this protocol (`retrieval_limit` 94, fetch depth 300, thresholdless semantic arm) every query's semantic list is the whole corpus, `_ppr_search` seeds from all of it, and `seed_vertices_for_memories` then selects **all 128 vertices for every query** — PPR with a full uniform reset set *is* global PageRank, and the judge measured the arm's ranked list **byte-identical across five queries including a nonsense query matching nothing in the corpus**. rg-0104/0105's consequence memory sits at constant rank 7 in that one list; its RRF voice 0.3/(60+7) lifts it from baseline 12/15 into top-10 on *every* query equally. That is the exact "global-popularity list fused into every query" `ppr_snapshot.py`'s own docstring forbids for the empty-seed case, arriving from the full-seed end — perturbation, the `w_importance` precedent's shape, and pre-registered bar rule 2 fails. Temporal (−0.39 MRR, −0.50 hit) is the same constant, time-blind list displacing gold siblings — structural at any weight, since every weight fuses the same list, scaled. No magnitude can therefore clear the bar and none was probed (anti-bar-shopping rule; the pre-registration conditioned further probes on constancy being *refuted*). No slice clears the per-slice sub-verdict either (every slice ΔMRR ≤ 0). **Design finding, reported not fixed (the judge may not edit ranking code):** seeding from the semantic list at `fusion_fetch_depth` ≥ corpus size degenerates the arm for any project under ~300 memories — production behaviour today, not an eval artifact. Query-conditioned PPR needs a bounded seed set (e.g. top-K semantic hits, K ≪ corpus); that is a T2.32-owner or successor-task change, and until it lands re-measuring this arm is pointless | `docs/eval/2026-08-06-retrieval-eval-arm-w_ppr.md` (canonical, run `500e272d`); `docs/eval/2026-08-06-retrieval-eval-arm-w_ppr-t250-verification.md` (judge re-run `fc32a172`); `docs/planning/analyses/2026-08-06-t2.50-preregistration.md` — corpus 94, gold v4, k=10, fingerprint `qwen3-embedding:0.6b|1024`, 0 live LLM calls |
| 2026-08-06 | `w_dual` / dual-level (built T2.94 over T2.49's vectors, judged T2.50; probe 0.3 plus a pre-registered 0.1 diagnostic leg) | Recorded run `a1b2b903`: aggregate ΔMRR **−0.1867**, Δhit@10 **−0.1667**; per-slice ΔMRR: exact 0.0000, fact −0.1111, knowledge-update −0.2832, multi-hop −0.1961, paraphrase −0.0278, temporal −0.5694, typo −0.2143; multi-hop hit +0.0714, temporal hit **−0.9167**. Judge verification run `cfcd0a50` (clean sha `594db59e`): **byte-identical deltas**, repairing the recorded row's dirty-tree attribution (`e4768c8f` predates prep commit `3f67152a`). Diagnostic leg `7310cdb0` at 0.1: aggregate ΔMRR −0.1285, Δhit +0.0098, temporal ΔMRR still **−0.3470** (11 of 12 pairs demoted; hit unchanged). Vacuous sibling row named per the disregard discipline: `2ae27407` (empty `relation_embeddings` partition — all-zero, not a measurement) | end_to_end p95: off 0.00360 s, on 0.00452 s recorded; one extra SQL round trip, no extra model call | Zero LLM tokens on either leg. The unpriced artifact economy here is the relation-vector refresh: this run embedded 62 relation phrases before the legs (LAN Ollama embed cost, amortised by T2.49's Tier-C job in production) | **Stays at weight 0.0; `dual_level_enabled` stays False.** Semantics stated before the multi-hop verdict (T0.06a): this channel **does not link entities at all** — it embeds terse relation phrases (`source rel_type target`, `relation_embeddings.py`) against the query vector and resolves matches to asserting memories via `memory_ids` (`hybrid_search.py`), so both SLICES.md ceilings are inapplicable in their own terms (effective 14/14: any memory asserting an embedded edge is reachable directly, no bridge required). The multi-hop gain fails bar rule 2 as perturbation, on three measurements: the flipped pair *changes with magnitude* (rg-0108 at 0.3, rg-0104 at 0.1 — a robust mechanism does not swap its wins when its voice shrinks); the consequence memories sit mid-list in the channel (rank 11 and 14) at similarity 0.41–0.49 inside a **non-discriminating score band** — the judge probed the channel's top phrases and unrelated edges score 0.44–0.60 for every query tried, including `'postfix DEPLOYED_ON mail-01'` at 0.44 against a door-badge query; and for rg-0108 the top-scoring phrase (0.60) is **memory A's own edge**, already at rank 1 in the baseline, so the channel's strongest signal duplicates what retrieval already had. Temporal is structurally broken, not magnitude-broken: relation phrases carry no time, both snapshot siblings assert same-shaped edges, and the damage persists at a third of the voice (−0.5694 → −0.3470). Aggregate ΔMRR is negative at both probed magnitudes, so bar rule 1 fails everywhere measured; the 0.1 leg was pre-registered as diagnostic and cannot activate anything under the anti-bar-shopping rule. No slice clears the sub-verdict (multi-hop's +0.0714 hit rides ΔMRR −0.1961 and rule-2 failure) | `docs/eval/2026-08-06-retrieval-eval-arm-w_dual.md` (canonical, run `a1b2b903`); `docs/eval/2026-08-06-retrieval-eval-arm-w_dual-t250-verification.md` (judge re-run `cfcd0a50`); `docs/eval/2026-08-06-retrieval-eval-arm-w_dual-w0.1-t250-diagnostic.md` (run `7310cdb0`); `docs/planning/analyses/2026-08-06-t2.50-preregistration.md` — corpus 94, gold v4, k=10, fingerprint `qwen3-embedding:0.6b|1024`, 0 live LLM calls |
| 2026-08-06 | Community injection (`community_injection_enabled`, judged T2.50) | **Unmeasured — and unmeasurable today**, recorded as a result per this gate's own text, never folded into the MRR verdict (doc 17 §2: it augments context, it is not a ranking signal). Two independently sufficient gaps, both verified in code: (1) the flag has **no consumer** — outside its `FEATURE_FLAGS_DEFAULTS` entry in `app/config.py` its only reference is a test pinning the default `False`, so there is no injection code path to measure; (2) the required metric is an answer-quality/groundedness delta on `memory_reason` over a **reasoning gold set**, which doc 17 §2 marks `(target-new)` and which exists nowhere under `scripts/benchlib/` | n/a — no measurement ran | n/a — no measurement ran | **Flag stays `False`.** Activating it would first need the injection path built and a reasoning gold authored with SLICES.md-grade decision procedures — gold-authoring plus feature work, the same honest floor T2.35's context axis was left at. Until both exist, any number offered for this flag should be distrusted on sight, and an MRR number for it would be a category error under the standing gate's own definition | This row; `docs/design/17-test-and-eval-harness.md` §2 |
| 2026-08-06 | `w_context_boost` / `applies_when` (T1.34 built it; T2.35 owns its magnitude) | **Unmeasured — measurement deferred, not attempted and failed.** The mechanism shipped in T1.34 (`match_context`, `CONTEXT_BOOST_FLAG`, the boost-plus-label and conflict-count hard rules) and is inert for one reason: `run_retrieval` declares no context and gold v4 carries no `env`/`version`/`situation` axis, so `match_context` returns the neutral outcome at every magnitude. There is no delta to report because there is no non-neutral leg to run | n/a — no measurement ran | n/a — no measurement ran | **Stays at weight 0.0.** Controller decision, 2026-08-06: the missing artifact is a context-bearing corpus, and authoring one now would measure a synthetic world at the cost of a day. The standing gate's own rule provides for this — *"an arm that cannot show its number stays at weight 0, and that outcome is recorded here as a result, not a failure"* — so the arm is closed as a result rather than held open. **Deferred to whole-system measurement after the implementation phase**, when a real corpus and real declared contexts exist; this gate applies per activation, so nothing is foreclosed. The hard rules are unaffected: they are not tunable and stay on at magnitude 0 | This row; `docs/design/07-retrieval-and-ranking.md` §6; T2.35 |
| 2026-08-06 | `w_heat` / `w_recency` (T2.29 built the substrate; T2.31 owns the activation) | **Unmeasured for activation — but the mechanism is live and proven, which distinguishes this row from the two above.** The signal was wired 2026-08-06 (`rank_fusion.heat_signal` / `recency_signal`, stamped on the shared channel's rows) and the arm demonstrably moves the order: aggregate ΔMRR **−0.3082**, Δhit@10 −0.1275 under the seed-and-freeze fixture. **That number is liveness, not activation**, and must not be read as "heat hurts": the seeded history is uncorrelated with relevance by construction (SHA-256 of each memory's own id, blind to the gold), so the on leg applies an essentially random multiplier and a random multiplier can only degrade MRR on average. A −0.31 aggregate is close to what a correctly-wired, uninformative arm should produce | end_to_end p95: recorded in the run artifact; all embeds cache-served | Zero LLM tokens — the arm reads one `memory_access_stats` row set, gated so both arms at zero pay nothing | **Stays at weight 0.0.** Controller decision, 2026-08-06: a realistic heat prior cannot be manufactured on the bench — any distribution it invents is either gold-correlated (which would make the arm win by construction) or gold-blind (which is the run above). **Deferred to whole-system measurement after the implementation phase**, when real `memory_access_stats` telemetry exists and heat correlates with retrievability for real reasons. The fixture, the freeze and the tests remain, so that later run is a command rather than a project | `docs/eval/2026-08-06-retrieval-eval-arm-w_heat.md`; `docs/planning/briefs/2026-08-06-t2.31-heat-recency-signals.md`; T2.31 |

---

## G-B — BLOCKING ENVIRONMENT FINDING (Tier 3, logged 2026-07-27)

**G-B cannot be cleared on this machine, and no amount of further Phase-1 task
completion changes that.** Recording it here rather than discovering it at T1.50.

**What was measured.** No LLM credential exists in any form: nothing in the
environment (`DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` all unset),
no `.env` (only `.env.example`), no Ollama binary and nothing serving on `:11434`
or any other local model port, and the real `darkmem` database has no schema, so no
`llm_purpose_configs` row supplies one either. This machine can make **zero** live
model calls.

**Why that blocks the gate specifically.** Two of G-B's three required numbers need
a live model, and this ledger already says so:

1. **Extraction F1 parity.** The stated tolerance above "judges G-B's live
   re-measurement under the Phase-1 prompt", and "G-B must be measured with the same
   model" (`deepseek-v4-flash`). The warm `--algo-only` cache cannot stand in: T1.17
   rewrites the extraction system prompt, and the per-entry cache key is
   `sha256(content + "\x00" + prompt)`, so **every one of the 36 entries is
   invalidated the moment T1.17 lands**. There is no path from the current cache to
   a post-T1.17 number.
2. **Retrieval eval vs the full-context baseline.** `run_retrieval_eval.py` exits
   non-zero with "DEEPSEEK_API_KEY is not set" — its smoke ingest runs extraction and
   classification against the vendor. Measured 2026-07-27: this is the step that
   turns `./scripts/gate.sh --full` RED today.

The third number, the isolation probe's zero-count (T1.35), is a database-level
property and is expected to remain reachable.

**Consequent task blockage.** T1.17 is blocked on a credential, which is a runbook §7
stop condition in its own right. Through it: **T1.18** and **T1.24f** (both depend on
T1.17), and therefore **T1.50** (depends on T1.24f). T1.52 and T1.54 additionally
need real data this machine does not hold.

**What is NOT blocked.** Everything else in E1 — roughly fifty remaining tasks —
neither needs a model nor feeds a number that does. Work continues there; only the
gate claim and the four tasks above are held.

**What a human needs to decide.** Either provision a `DEEPSEEK_API_KEY` for the same
`deepseek-v4-flash` alias the T0.05 baseline used, or change how G-B is measured —
which is a Tier-3 amendment to the gate's definition and explicitly not an agent's
call. Note the two pre-existing recorded gaps above compound this: there is no
latency/token twin for the baseline, and "same model" is asserted rather than
verifiable, so a late-provisioned key should also capture response metadata per this
ledger's own requirement.

**Do not work around this.** Widening the tolerance, substituting a different model,
or citing the warm cache as a post-T1.17 measurement would each convert a missing
number into a false one, which is the failure this ledger exists to prevent.

---

## G-B — WHAT THE F1 NUMBER CAN AND CANNOT EVIDENCE (measured, 2026-07-28)

**G-B's extraction-F1 parity number is real evidence of the model's extraction quality and
weak evidence of the pass chain's correctness.** Three independent measurements now show the
36-memory gold corpus cannot see large parts of the chain it is being used to guard. Recorded
here because T1.50 must word its claim against this, not around it.

**Measurement 1 — Stage 3 (`relation_rescue`) is invisible.** T1.25 ablated it four ways
(flag off, each of three passes dropped): **0.000 delta on all eight dimensions**, output
bit-identical across all 36 memories. The layer alters **one** memory and contributes **one**
surviving triple, which duplicates one the model already emitted. Independently re-measured
by the controller.

**Measurement 2 — seven of Stage 4's ten passes are invisible.** T1.24d's planning pass ran a
per-pass ablation over all 36 memories using the harness's own `without()` primitive, with
baselines reproducing exactly. Only three passes move anything at all:

| Pass | gold Δ rel_full | gold changed | held-out Δ rel_full | held-out changed |
|---|---|---|---|---|
| `remap_to_valid_entities` | −0.045 | 3/26 | −0.022 | 1/10 |
| `downgrade_future_to_mentions` | −0.012 | 1/26 | 0.000 | 0/10 |
| `drop_date_misuse` | −0.012 | 1/26 | 0.000 | 0/10 |
| the other **seven** | 0.000 | **0/26** | 0.000 | **0/10** |

So **"relation F1 does not regress" is satisfiable by deleting 70% of Stage 4.** And the
blind passes are the worst possible ones to be blind to: `gate_replaces_selection`,
`gate_replaces_requires_verb`, `drop_edges_to_negated` and the direction validators — whose
shared failure mode is **a false `REPLACES` reaching supersession**. Supersession flips a
memory out of the default view; a false one silently removes a live memory, which is the
exact failure `chk_superseded_has_pointer` and the six-rule gate exist to prevent.

**Measurement 3 — the vocabulary widening was never measured at all.** T1.23 widened
`MEMORY_TYPES` 7 → 9 and recorded that the F1-green did not cover it: the bench cache key is
`sha256(content + "\0" + system_prompt)`, while the widened schema string rides the **user**
message. It has been carried on an unmeasured assumption since it landed. T1.17's live
re-record is its first real measurement.

### What this means for T1.50

- **Do not cite F1 as evidence for Stage 3 or for the seven blind Stage-4 passes.** A flat
  delta across an ablation is evidence of *nothing measured*, not of *no regression*.
- **T1.24f's "per-pass contribution recorded" box must record these passes as
  `unmeasurable on this corpus`, not as `zero contribution`.** Those are different claims and
  only one is true.
- The substitute evidence is behavioural: per-gate tests, named mutation proofs, and
  order-insensitive whole-chain diffs. T1.24d's plan builds that guard; it is what should be
  cited where F1 cannot reach.
- **The honest form of the G-B claim** is parity of *model extraction quality* against the
  T0.05 baseline, plus behavioural coverage of the pass chain — not "the extraction chain is
  verified by F1".

### The underlying cause, and who could fix it

The corpus is 36 memories chosen to exercise the model, not the pass chain. Closing this is
**gold-set authoring**, which the runbook routes to Fable tier and which no current task
owns. It is deliberately **not** being added as a task now: it does not block G-B provided
G-B's claim is worded to match what was actually measured, and inventing gold cases to make
a guard light up is the fitted-evidence failure the `phoenix v2` ruling already rejected.

### Sharpening of Measurement 3, and a controller correction (2026-07-28)

T1.17's planning pass established the precise form, and the controller confirmed it: the
bench cache key is `sha256(content + "\0" + system_prompt)`, `EXTRACTION_SCHEMA` rides the
**user** message, and `MEMORY_TYPES` is **already 9**. So the 36 outputs cached on 2026-07-26
under the **7-type** schema are still being served on every `--algo-only` run.

**The F1 merge gate has therefore been green over a configuration nobody runs since T1.23
landed.** Two things follow, and they are different:

- The **wave-to-wave comparisons remain valid.** Every run this session replayed the same
  cache, so a change in the number was a real change in the pass chain. Nothing reported as
  a delta was wrong.
- The **absolute number describes a stale configuration.** It is not the F1 of the shipping
  extractor and must not be presented as such at G-B.

T1.17's re-record is what closes this — and its Done-when box asking `run_bench.py` to
exercise the merged shipping path with its gate state pinned is precisely the fix, which is
why that box matters more than it reads.

**Controller correction:** T1.17's brief described capturing response metadata (model string,
token counts) as *an opportunity*. That was wrong. This ledger already records it as a
**requirement** — "'silent vendor update' must not be accepted as an explanation for a
shortfall unless the G-B runner captured response metadata showing what was actually served".
The re-record is the measurement G-B cites, so it must capture that metadata. The plan is to
treat it as required.

**Blast radius, recorded for T1.50:** the prompt edit invalidates more than the 36 extraction
entries. `benchlib` keys its cache on the whole `messages` list, so T1.50's retrieval
baseline — roughly 94 cached extraction calls plus the ingested graph itself — dies with it.
T1.17's task text does not warn about this, and T1.50's brief must budget for re-establishing
that baseline after the prompt change rather than before.

---

## G-B — THE BASELINE NO LONGER REPRODUCES. Measured 2026-07-28, decision recorded.

The gate ledger's own recorded gap — *"'same model' is asserted, not verifiable"* — has now
been tested against a live model and **the baseline does not reproduce**. 159 live calls,
evidence committed at `docs/eval/2026-07-28-laneD-live-model-drift/`.

**32 of 36 raw outputs differ; 15 of 36 (42%) differ semantically after `clean_extraction`.**
Two controls rule out the innocent explanations: the same content at the same seed run three
times is byte-identical and differs from the cache *the same way each time*, and a
`temperature=0` control still leaves 4 of 5 differing. This is vendor-side drift, not
sampling noise and not a config mismatch. The cache was **not** re-recorded.

### The three-arm decomposition — the part that matters

| Arm | Algorithm | Raw source | gold | held-out |
|---|---|---|---|---|
| **A** — recorded T0.05 / G-A | 2026-07-26 | cache | 0.925 / 0.955 / 0.865 / 0.892 | 0.893 / 0.929 / 0.667 / 0.667 |
| **B** — today's algo, cached raw | `dbde017` | cache | 0.940 / 0.970 / 0.895 / 0.921 | 0.949 / 0.983 / 0.872 / 0.872 |
| **C** — today's algo, **live** raw | `dbde017` | live | 0.925 / 0.970 / 0.921 / 0.921 | 0.862 / 0.931 / 0.765 / 0.765 |

**B − A is the deterministic passes' gain. C − B is the isolated model drift**, which is
roughly neutral on gold and **materially negative on held-out across all four dimensions**
(`−0.087 / −0.052 / −0.107 / −0.107`).

**All eight cells still clear the G-B floors.** But two facts qualify that pass:

1. Held-out entity name+type declines against A, `0.893 → 0.862`. At that cell's flip cost of
   `2/56 = 0.0357`, **drift alone has consumed 0.87 of the tolerance's 1.0-flip "silent
   vendor-side model update" allowance** — it lands just inside a budget written for exactly
   this event, and it is 87% spent on the first measurement.
2. **The deterministic passes are masking the drift.** On held-out relations the algorithm
   gained `+0.205` while the model lost `−0.107`, netting `+0.098`. A parity check comparing
   Phase-1 against A passes *partly because T1.24's algorithm gains are paying for model
   regression*, and the comparison cannot show that.

### Controller decision (the human delegated this; recorded rather than asked)

**The bar is not moved and the baseline is not re-recorded.** Arm A stays the reference.
Runbook §7 forbids widening a bar to fit a result, and re-baselining onto a model that has
already drifted once would make "parity" a comparison against a moving target.

**Instead, T1.50 must report the three-arm decomposition, not a single parity number.** The
honest claim is: parity against A holds, *and here is how much of that is algorithm and how
much is model*. A headline number that hides a −0.107 model regression under a +0.205
algorithm gain is technically true and materially misleading, which is the failure this
corpus exists to prevent.

**The verifiability gap is now closable.** The run captured
`system_fingerprint = fp_8b330d02d0_prod0820_fp8_kvcache_20260402`, stable across all 159
calls. Every future live run must record it. That converts "same model is asserted" into
"same model is checkable", which is what the recorded gap asked for — and it means the *next*
drift will be detectable at the moment it happens rather than two days later by accident.

**If drift widens before G-B, the subsidy is already spent** and the comparison against A will
fail rather than merely mislead. That is the gate working; report it and leave G-B open.

### Two other results from the same run

- **The retrieval eval works and its twin exists.** MRR `0.8582` / hit@10 `0.8431` against
  full-context `0.9069` / `0.9314`, reproducing G-A byte-identically despite 100 live ingest
  calls — hybrid search never touches the entity graph, so extraction drift cannot reach it.
  Token cost recorded (939,668 prompt / 12,125 completion), which **retires G-A's
  `cost-unmeasured` caveat** with real numbers.
- **The five-phase pipeline ran end to end against live models for the first time**: 94
  memories, 131 entities, 63 relations, **0 pipeline failures**, exactly one fingerprint
  (`qwen3-embedding:0.6b|1024`, no rotation), 0 non-lowercase entity names.

---

## G-B — T1.17 live re-record. Evidence, not a verdict. Measured 2026-07-28.

T1.50 owns the G-B verdict and the probe rows. What follows is the measurement T1.17 was
scheduled to produce: the F1 bench moved onto the shipping request, the cache re-recorded
live, and the prompt strip measured as its own arm.

**72 live calls** against `deepseek-v4-flash` — two passes of 36 (26 `gold.json` + 10
`gold_heldout.json`). The 36-call control arm the T1.17 plan budgeted was **dropped**: lane D
already ran it, and run through current code it could not have isolated drift anyway, because
the 9-type `EXTRACTION_SCHEMA` rides the user message. Budget spent: 2 passes of the 2
expected, 0 prompt revisions of the 1 allowed.

`system_fingerprint = fp_8b330d02d0_prod0820_fp8_kvcache_20260402` on **all 72 calls**, equal
to lane D's. The bench now pins that string and **exits non-zero mid-run** if the served stack
rotates, so a vendor swap can no longer fold fresh drift into a measured delta unnoticed.
Model string `deepseek-v4-flash` and the usage envelope are captured per cache entry.

### The five arms

Cells are `entity name+type / entity name only / relation full triple / relation pair`.

| Arm | Algorithm | Prompt | Gate | Raw | gold | held-out |
|---|---|---|---|---|---|---|
| **A** — recorded T0.05 / G-A | 2026-07-26 | `775ca7c4` | extract-only | cache | 0.925 / 0.955 / 0.865 / 0.892 | 0.893 / 0.929 / 0.667 / 0.667 |
| **B** — today's algo, cached raw | `dbde017` | `775ca7c4` | extract-only | cache | 0.940 / 0.970 / 0.895 / 0.921 | 0.949 / 0.983 / 0.872 / 0.872 |
| **C** — today's algo, live raw | `dbde017` | `775ca7c4` | extract-only | live | 0.925 / 0.970 / 0.921 / 0.921 | 0.862 / 0.931 / 0.765 / 0.765 |
| **Pass A** — T1.17, prompt unchanged | `48d3c0d` | `775ca7c4` | **merged** | live | 0.925 / 0.970 / 0.853 / 0.853 | 0.881 / 0.949 / 0.895 / 0.895 |
| **Pass B** — T1.17, prompt stripped | `48d3c0d` | `f59a62d1` | **merged** | live | 0.912 / 0.971 / 0.857 / 0.857 | 0.967 / 0.967 / 0.950 / 0.950 |

Floors: gold `0.881 / 0.910 / 0.784 / 0.811`; held-out `0.786 / 0.821 / 0.485 / 0.485`.

**All eight Pass B cells clear their floor.** So do all eight Pass A cells. The held-out
relation cells clear by a wide margin, so the one-way cascade valve was not reached and no
`--diffs` triage was owed.

### The decomposition, which is the point

- **Pass A − arm C = the merged classification fields**, same day, same schema width, same
  prompt, same served stack. gold `0.000 / 0.000 / −0.068 / −0.068`; held-out
  `+0.019 / +0.018 / +0.130 / +0.130`. Folding classification into the extraction call moves
  relation extraction in **opposite directions on the two gold files** — it costs 0.068 on
  gold and gains 0.130 on held-out. Both stay above the floor, and gold's `rel_pair` retains
  ~1.6 flips of headroom, but the sign flip is worth naming rather than netting: this is one
  measurement of a change that alters what the model is asked to produce in a single response.
- **Pass B − Pass A = the prompt strip.** gold `−0.013 / +0.001 / +0.004 / +0.004`; held-out
  `+0.086 / +0.018 / +0.055 / +0.055`. The strip is close to neutral on gold and positive on
  held-out — consistent with a strip that removed only rules the schema string or a
  deterministic pass already carries (audit below). It is **not** evidence that a larger strip
  would be neutral.
- **Arm C − arm B** remains lane D's drift arm, and per the T1.17 review it is honestly
  labelled **"drift + the 7→9 schema widening, not separable"**: arm B's raws were recorded
  under the 7-type user message, so part of the held-out `−0.087 / −0.052 / −0.107 / −0.107`
  is T1.23's request change rather than vendor weights.

### What changed in the harness, and why the absolute number now means something

The bench previously keyed its cache on `sha256(content + "\0" + system_prompt)` and assembled
its own request. Both are fixed:

- The request comes from `ExtractionService.build_extraction_request` — the same function the
  pipeline calls. The bench keeps its own `clean_extraction` call so the cache still stores
  **raw** output and `--algo-only` re-scores the deterministic passes for free.
- The key now covers the whole assembled request, so the schema string, the taxonomy width and
  the merge gate all key. This closes the staleness recorded above: between T1.23 landing and
  today, `--algo-only` replayed outputs produced by a request the code no longer sent.
- `.cache/manifest.json` records the prompt and schema fingerprints, the gate, the model, the
  git sha and the served fingerprints. `--algo-only` **exits non-zero naming the mismatching
  field** rather than silently replaying a stale generation.
- The bench asserts the configured extraction model equals `deepseek-v4-flash` and fails loud
  otherwise, since the ledger fixes the model for parity.

### The prompt strip was small, and that is the finding

`775ca7c45ed9a06a` → `f59a62d1be7273a8`; 35,665 → 35,188 characters. **4 rules stripped, 1
stale statement corrected, ~44 kept.** Doc 05 §6's "strip every rule the passes already
enforce" assumes deterministic twins that mostly do not exist yet: rule 2a's 28-builtin filter
is carried by `_NOISE_NAMES` for **10 of 28**; nothing at all covers rule 2b (config values and
CSS tokens) or rule 9h-dir (`CAUSES` root→symptom, the largest uncovered recall surface); and
`weight` (rule 14) has no downstream enforcement while `_prefer_relation` still consumes it.
Evidence per rule, and the six pass gaps handed to T1.24b–e, are in
`docs/eval/2026-07-28-T1.17-prompt-rule-audit.md`.

### Artefacts

- `docs/eval/2026-07-28-T1.17-merged-prompt-cache/` — Pass B's 36 raws + manifest. The
  generation `--algo-only` replays; the README carries the cross-worktree restore.
- `docs/eval/2026-07-28-T1.17-passA-cache/` — Pass A's 36 raws + manifest, the other arm.
- `docs/eval/2026-07-26-T0.05-extraction-baseline-cache/` — untouched, and now replayable
  **only at a commit before T1.17**: both the key definition and the prompt changed.

### Still open for T1.50

The `benchlib` retrieval cache — roughly 94 cached extraction calls **and the ingested graph
the accuracy numbers were computed over** — is invalidated by this prompt change, as recorded
above. T1.17 did not pay it and did not re-run the retrieval eval.

---

## G-B — T1.24f whole-chain F1 parity. Evidence, not a verdict. Measured 2026-07-28.

T1.50 owns the G-B verdict. This section records the whole-chain parity measurement at
`f4eac77`, `--algo-only` over T1.17's Pass-B cache, zero live calls. Full method,
arithmetic and per-memory traces: `docs/eval/2026-07-28-T1.24f-whole-chain-parity.md`.

**Baseline cited: arm A** (T0.05 recorded), per the standing controller decision — the
bar did not move, the tolerance was not widened, no live calls were made.

### The eight cells (`ent_nt / ent_n / rel_full / rel_pair`)

| Set | Arm A | Floor | Measured | Δ vs A | Flips spent | Verdict |
|---|---|---|---|---|---|---|
| gold | 0.925 / 0.955 / 0.865 / 0.892 | 0.881 / 0.910 / 0.784 / 0.811 | **0.912 / 0.971 / 0.883 / 0.883** | −0.013 / +0.016 / +0.018 / −0.009 | 0.87 / 0 / 0 / 0.33 | all pass |
| held-out | 0.893 / 0.929 / 0.667 / 0.667 | 0.786 / 0.821 / 0.485 / 0.485 | **0.967 / 0.967 / 0.950 / 0.950** | +0.074 / +0.038 / +0.283 / +0.283 | 0 / 0 / 0 / 0 | all pass |

**All eight cells clear their floors; the cascade valve was not engaged.** Stated plainly
per ruling: parity against arm A holds. The two cells below A are gold ent_nt (0.87 of 3
flips) and gold rel_pair (0.33 of 3 flips).

### The decomposition, which T1.50 must report instead of a headline

Algorithm total (deterministic-pass legs B−A plus T1.24e's +0.026 gold-relation
narrowing) vs model-side total (drift+widening, merge, strip — everything that changed
what the model was asked or served):

| Cell | Algorithm | Model-side | Net vs A |
|---|---|---|---|
| gold ent_nt | +0.015 | −0.028 | −0.013 |
| gold ent_n | +0.015 | +0.001 | +0.016 |
| gold rel_full | +0.056 | −0.038 | +0.018 |
| gold rel_pair | +0.055 | −0.064 | −0.009 |
| held-out ent_nt | +0.056 | +0.018 | +0.074 |
| held-out ent_n | +0.054 | −0.016 | +0.038 |
| held-out rel_full | +0.205 | +0.078 | +0.283 |
| held-out rel_pair | +0.205 | +0.078 | +0.283 |

**The deterministic passes are subsidising drift.** The raw drift(+widening) leg is
−0.087/−0.052/−0.107/−0.107 on held-out; parity there holds because the algorithm's
+0.205 and the request-change gains outweigh it. On gold the dominant model-side cost is
the merge (−0.068 on both relation cells), partially paid back by T1.24e's +0.026. Leg
values are path-dependent (measured at `dbde017` / `48d3c0d` respectively) and C−B
remains "drift + 7→9 widening, not separable".

### Per-pass contribution — recorded, with the blind set named

All 31 registry entries re-ablated at **one** generation (`f4eac77` over the Pass-B
raws), superseding the split-generation stage tables for current use. Census: **18 of 31
entries are bit-identical on removal across all 36 memories** — 5/8 of Stage 1, 2/4 of
Stage 2, 2/3 of Stage 3, 6/10 of Stage 4, 3/6 of Stage 5 — and are recorded as
**unmeasurable on this corpus, not zero contribution**. One more (`normalize_names`) is
score-invisible while changing one memory. Twelve move a score; the largest is
`rescue_relation_endpoints` (−0.200 held-out rel_full on removal — most of the held-out
relation gain is this one pass), then `fan_out_coordinated` (−0.094 gold / −0.117
held-out). **G-B may not cite F1 as evidence for any bit-identical pass**; the guards
there are the behavioural suites and mutation proofs.

Two additions to the standing rulings:

- **The blind set's membership is generation-relative.** `suppress_temporal_edges`
  (blind for T1.24d) is now visible on both sets; `remap_to_valid_entities`' held-out
  leg vanished and its gold effect went mixed-sign; T1.24b's measured `filter_noise`
  gain is now invisible. The prior stage counts stay true of their generations; this
  table is the current one.
- **`rescue_relations_subject_tracking` is a measured net negative on this generation**
  (+0.012 gold relations on removal; spurious `search USES meilisearch` on e1; zero
  productive firings in 36 memories). Reported, not fixed — Stage 3 is T1.25's surface.

### Findings and provenance

- **The `gateway` gold/prompt disagreement now costs a number.** The model obeys prompt
  rule 7b (`gateway :artifact`); gold e14 says `service`; the substitution is exactly one
  flip and is the **entire** gold ent_nt shortfall vs A (fixing that one key yields
  0.926 ≥ 0.925). The 2026-07-27 amendment's "no number moves on it today" no longer
  holds. Re-adjudication stays with the gold-set owner; the key was not changed
  mid-parity.
- **Prompt-in-disguise audit: clean.** No pass added by T1.24b–e re-implements a
  surviving prompt rule; the two deliberate rule/pass overlaps (rule 7b ↔
  `rescue_relation_endpoints`, rule 10 ↔ `filter_negation_only`) are backstops, the
  first measured as heavily load-bearing. The six T1.17 pass gaps remain open, so the
  corresponding rules stay unstrippable.
- **Provenance:** cache = Pass-B generation, manifest `prompt f59a62d1 / schema 34e62626 /
  gate merged / model deepseek-v4-flash`, fingerprint
  `fp_8b330d02d0_prod0820_fp8_kvcache_20260402`; the manifest guard was **proven** (a
  corrupted `prompt_sha16` fails exit-1 naming the field, restore replays identically);
  exactly 36 of the 72 cache entries are reachable by the current assembly; both gold
  files untouched since `ef12ff1`. Residual trust: cached raw entries carry no per-entry
  checksum.
- Floors green at expected counts: backend `2225 passed`, benchlib `284 passed`.

---

## G-B — VERDICT: CLEARED. Measured 2026-07-28, T1.50.

Owning task T1.50, chartered adversarially: the run was executed to find the reason
this gate should not clear, and what follows is what survived. Lane `feat/e1-lane-a`
at `16f8fb0` (identical to the epic head — base proof in the T1.50 report). Databases
`darkmem_test_1` / `darkmem_bench_1` throughout; the real `darkmem` database was never
named, opened, or read. Verify commands actually run, real output in the T1.50 report:
`./scripts/gate.sh --full` → **GATE GREEN, exit 0** (alembic single-revision; backend
**2478 passed**; frontend typecheck + **523 tests** + build; benchlib **284 passed**;
F1 `--algo-only`; retrieval eval; API e2e **3 passed / 1 skipped**; playwright
**26 passed / 1 skipped**; port hygiene clean), plus the standalone
`run_isolation_probe.py` → **0 violations, exit 0**, and a held-out `--algo-only`
replay (the gate's F1 step covers `gold.json` only).

### Probe 1 — extraction F1 parity: PASS, reported as the decomposition

`--algo-only` at `16f8fb0` over the Pass-B cache (manifest `prompt f59a62d1 /
schema 34e62626 / gate merged / model deepseek-v4-flash /
fp_8b330d02d0_prod0820_fp8_kvcache_20260402`) reproduces T1.24f's eight cells exactly:
gold `0.912 / 0.971 / 0.883 / 0.883` against floors `0.881 / 0.910 / 0.784 / 0.811`
(flips spent vs arm A: 0.87 / 0 / 0 / 0.33); held-out `0.967 / 0.967 / 0.950 / 0.950`
against floors `0.786 / 0.821 / 0.485 / 0.485` (0 flips; the cascade valve was not
reached, so no `--diffs` triage is owed). The extraction surface is untouched between
`f4eac77` (T1.24f's measurement) and this head — verified by git diff, not assumed.

**The claim is the decomposition, never the headline** (standing controller decision,
2026-07-28): per cell, algorithm vs model-side legs are the T1.24f table
(`docs/eval/2026-07-28-T1.24f-whole-chain-parity.md`). The deterministic passes are
subsidising vendor drift — the raw drift(+widening) leg is
`−0.087 / −0.052 / −0.107 / −0.107` on held-out, and parity holds because the
algorithm's `+0.205` on held-out relations (most of it one pass,
`rescue_relation_endpoints`) and the request-change gains outweigh it. A bare "parity
holds" hiding that is technically true and materially misleading; this verdict does
not make it. The honest form: **whole-chain output parity against arm A holds, decomposed
as stated; it is not evidence that the vendor's extraction quality is unchanged.**

What this number may and may not evidence:

- It evidences merged-path extraction quality at the Pass-B generation and the twelve
  score-visible passes. It may **not** be cited for Stage 3 (all three passes), the
  seven blind Stage-4 passes, or the three blind Stage-5 passes — **18 of 31 registry
  entries are bit-identical on removal: unmeasurable on this corpus, NOT zero
  contribution.** The guards there are the behavioural suites and their recorded
  mutation proofs (`test_relation_rescue.py`, `test_relation_gating.py`,
  `test_collapse_fanout.py`). F1 also cannot distinguish T1.24e's tie-break narrowing
  from a full revert; `test_weight_alone_would_have_kept_the_backwards_edge` is the
  only separating artifact.
- gold ent_nt `0.912` — the one cell below A, at 0.87 of 3 flips — is **not** read as
  chain regression: the entire shortfall is the one `gateway` answer-key/prompt
  adjudication conflict (the model obeys prompt rule 7b's `artifact`; gold `e14` says
  `service`; adjudicating that single key restores 0.926 ≥ A's 0.925). The key was not
  changed mid-parity; re-adjudication stays with the gold-set owner.

**The baseline-drift qualification.** The recorded baseline no longer reproduces
against the live vendor (42% of outputs differ semantically, measured 2026-07-28 with
controls ruling out sampling noise and config mismatch). Arm A stays the reference by
controller decision; the bar did not move. Two consequences carried, not buried:
drift alone has already consumed **0.87 of the 1.0-flip vendor-update allowance** on
held-out ent_nt at its first measurement, so **the subsidy is spent** — if drift widens
before the next live re-measurement, the comparison against A fails rather than
misleads, and that will be the gate working; and the verifiability gap is closed only
on the F1 bench side (manifest pins the served fingerprint and aborts mid-run on
rotation) — see the residual under probe 2.

### Probe 2 — retrieval eval vs full-context, WITH its twin: PASS, no regression, none silent

Artifact `docs/eval/2026-07-28-retrieval-eval.md` (run `6b7b0c0d`, git `16f8fb0`;
lane D's same-day cache replay is preserved at
`docs/eval/2026-07-28-retrieval-eval-laneD-replay.md`). This run **paid the
re-establishment the ledger charged to T1.50**: T1.17's prompt change had invalidated
the ~94 cached ingest extraction calls, and the gate run re-recorded them live under
the merged prompt (ingest 100 live calls total: 94 extraction + content/entity embed
chunks against the LAN Ollama; retrieval and full-context arms 0 live).

- **Accuracy, per slice (rule 4), byte-identical to G-A's recorded numbers on all
  seven slices.** Pooled: retrieval MRR 0.8582 / hit@10 0.8431 vs full-context 0.9069 /
  0.9314 (Δ +0.0487 / +0.0882, full-context minus retrieval) — the inherited headroom
  E2's graph arms exist to close, stated plainly, not a failure of this gate.
  `multi-hop` retrieval hit@10 = 0.0000 remains the DESIGNED state (T0.06a).
  `temporal` remains the one slice where retrieval beats full context on hit@10
  (1.0000 vs 0.6667). No cell moved: nothing regressed, so nothing regressed silently.
  That extraction re-sampling cannot move these numbers is itself measured (three
  generations now score identically), because hybrid retrieval never reads the graph.
- **Twin.** Token cost: the retrieval arm's indexing work is now **live-measured** —
  94 extraction calls, **927,166 prompt / 11,661 completion** (926,080 vendor-cache-hit
  prompt); the full-context arm is 102 cache-served calls at **472,558 / 3,899**,
  recurring per query set. Per the recorded caveat the two are different kinds of
  quantity and are never subtracted or ratioed. p95 latency: end-to-end 0.00303 s
  retrieval / 0.00023 s full-context, both cache-served populations — the
  `latency-no-live-samples` caveat is present and honest, the same treatment G-A's
  PASS used; the live-population channels are semantic_search p95 0.00184 s and
  keyword_search p95 0.00056 s per query against the bench database.
- **Reproducibility exercised, not asserted:** a second run replayed everything from
  the now-warm cache (0 live calls) with identical magnitudes reclassified live→cache,
  and a third run reproduced the second's canonical JSON block **byte-for-byte** — the
  runner's contract holds on the exact pair it covers.
- The exclusion envelope is **not** cited as evidence that isolation removed nothing
  (standing T1.44 ruling); that evidence is probe 3.
- **Residual, recorded:** benchlib's live ingest entries capture the full usage
  envelope but **no served-model string or system fingerprint**, so the ingest-side
  cost twin is attributable to "what DeepSeek served on 2026-07-28" by assertion. It is
  non-load-bearing for the accuracy claim (see above), but the capture should be
  extended before any gate leans on ingest-side cost comparisons.

### Probe 3 — isolation probe: PASS, exactly 0

`run_isolation_probe.py` against `darkmem_bench_1` at `16f8fb0`: **0 violations,
exit 0** across all 17 registry surfaces, with per-surface row widths identical to the
recorded 10-violation run (`memory_reason` 16, `chat_retrieval` 8,
`chat_history_citations` 9, `reembed_backfill_queue` 3) — the zero was made by
labelling, never by narrowing. The informational lists are unchanged and remain
reported-not-counted per Rulings 4/5: I1 id-only exposure (13 sightings; closed by
decision at T1.60 — entities are deliberately not memory-scoped) and I2 retention
snapshots (3 sightings; the escalated Tier-3 question below).

### Cited alongside the parity audit, so this verdict says it too

The two-door parity table (`docs/two-door-parity.md`: 43 surfaces, 13 two-door, 29
single-door with stated reasons, 0 divergent after T1.42f) is cited **with** its
recorded amendment: doc 12 §3's claim that all eleven code tools ship with a REST twin
was false — six (`code_context`, `code_dependencies`, `code_changes`,
`code_communities`, `code_processes`, `code_rename`) have no REST route and are
recorded MCP single-door with stated reasons, which invariant 17 permits. That
decision is recorded **REVERSIBLE** (building the six twins is the alternative the
owner may still take). Five of the six are filtered projections of rows
`GET /code/graph/{repo_id}` serves whole; **`code_changes` is the one genuine
capability asymmetry** — it reads the uncommitted working tree and no REST read
carries uncommitted state.

### The dead-guard audit this verdict ran on itself

This session recorded **twelve guards that could not fail** — tests importing the
constant they defend, checks reading the artifact the fix writes, specs asserting DOM
attributes nothing writes — several in code this gate now measures. Considered
explicitly per number: the **isolation zero** rests on an instrument with proven
discriminating power (mutation drove 10 → 58 → 10; two byte-identical runs; the
registry-completeness guard fails the build on an unclassified door; and the recorded
10-violation FAIL is itself proof the probe can say no). The **F1 cells** rest on the
manifest guard (mutation-proven: a corrupted `prompt_sha16` exits 1 naming the field)
and a scorer that reproduced T0.05 byte-for-byte at G-A; where F1 is blind, the
substitute behavioural guards carry recorded mutation proofs — one (the fan-out
ordering guard) needed strengthening twice before it could fail, which is recorded,
and the stated residual stands: cached raw entries carry no per-entry checksum. The
**retrieval numbers** rest on the runner's reproducibility contract (exercised twice
today, byte-identical) and the no-twin-no-accuracy guard at the `ledger.record`
boundary. **No number certified here rests on a guard from the recorded dead set** —
each of the twelve was fixed, replaced, honestly re-scoped, or deleted before this
run, with its episode in the amendment log.

### e2e evidence status — the 2026-07-27 "vacuous `--full`" caveat is discharged by measurement

That ruling said a green `--full` was not e2e evidence while all 7 playwright specs
soft-skipped. T1.64 rebuilt the suite; this run executed real assertions: API e2e
3 passed / 1 skipped, playwright 26 passed / 1 skipped. Both skips are named and
environmental, not soft-skip rot: the API e2e **search leg skips loudly** because this
sandbox has no reachable embedder for the disposable stack (the skip message names the
`pipeline_failures` row), and `setup-wizard-refresh` skips on an already-initialized
stack via the T1.64-narrowed guard. Search-over-ingested-content is separately proven
in the same gate run by the retrieval eval's 102 scored pairs. Relatedly, the
2026-07-27 hold "G-B may not claim doc 05 §2 until T1.14 lands" is discharged: T1.14
landed the front-door cutover and this run's e2e capture test exercises the buffered
202 contract on the shipped doors.

### Standing obligations this verdict does NOT discharge

Named here so the phase advance cannot silently absorb them; none is one of G-B's
three probes, and the numbers above pass regardless.

1. **The Tier-3 content-retention escalation still has no owner.** The 2026-07-27
   ESCALATION row records "needs an owner before G-B": deleted-memory content survives
   in the `events` journal and in `messages.context` citation snapshots, pinned by
   test, options written up in T1.29e's report, decision human-only. It sits outside
   the isolation bar by ratified Ruling 4 (I2 reported-not-counted), so it cannot move
   probe 3 — but the controller must assign the owner at merge time or overrule this
   verdict.
2. **The drift subsidy is spent.** The next live F1 re-measurement inherits ~0.13
   flips of vendor allowance on held-out ent_nt; a further drift event fails parity
   against A outright.
3. **Ingest-side served-model metadata is not captured** by benchlib's cache (probe 2
   residual).
4. The `gateway` gold-key adjudication remains with the gold-set owner; until then
   gold ent_nt carries a one-flip spend that is an answer-key conflict, not a chain
   regression.

### Verdict

All three numbers hold at their stated bars, none silently, none by a widened bar, and
none by a re-run-until-green. **G-B: CLEARED, 2026-07-28.** Phase 2 may be entered.
Carried forward as G-C's inheritance: the four standing obligations above, the
18-of-31 F1-blindness census (behavioural suites are the guard where F1 cannot see),
and the full-context-beats-retrieval headroom (+0.0487 MRR pooled) that E2's graph
arms exist to close.

---

## 2026-08-27 — serving-stack rotation, and the Phase 1/2 prompt work

### The vendor rotated, and the guard caught it

`run_bench.py`'s `EXPECTED_SYSTEM_FINGERPRINT` refused a live run:
DeepSeek stopped serving `fp_8b330d02d0_prod0820_fp8_kvcache_20260402` and
now serves `a26a7955944dc5c60445bff77fac9c8e`, stable across five
consecutive probes on 2026-08-27. The guard is the reason this entry can
attribute anything at all.

**The floors were re-recorded live on the new stack with the prompt
unchanged**, before any prompt edit was measured. That run is the only
honest comparison point, because the vendor's drift is positive and larger
than the prompt effect:

| dimension | old stack 2026-07-27 | new stack, same prompt | vendor drift |
|---|---|---|---|
| Entity (name+type)  | 0.912 | 0.933 | +0.021 |
| Entity (name only)  | 0.971 | 0.978 | +0.007 |
| Relation (s,TYPE,t) | 0.883 | 0.921 | +0.038 |

Measuring a prompt change against the 2026-07-27 numbers would have
credited the vendor's improvement to the prompt. Both prompt fingerprints
below were measured on `a26a7955944dc5c60445bff77fac9c8e`.

### The prompt change, measured same-stack

`f59a62d1be7273a8` → `606a42eef2e5d30a`; 35,188 → 32,265 characters
(-2,923, ~-730 tokens on every ingest).

| dimension | A: old prompt | B: new prompt | delta |
|---|---|---|---|
| Entity (name+type)  | 0.933 | 0.956 | +0.023 |
| Entity (name only)  | 0.978 | 0.985 | +0.007 |
| Relation (s,TYPE,t) | 0.921 | 0.935 | +0.014 |

**Read these deltas as "no harm", not as a demonstrated gain.** The gold
carries 69 entities and 39 relations, so every delta above is one or two
items: entity true positives moved 63 → 65, relation true positives 35 → 36.
That is inside the noise a 39-relation bench can resolve. What the run
supports is that the diet and the two rule corrections did not cost
accuracy while removing ~730 tokens from every ingest; it does not support
a claim that they improved it.

### What changed in the prompt

Two corrections and a diet:

- **Rule 10's worked example ordered `OpenAI REPLACES Anthropic`** for
  "considered Anthropic but went with OpenAI" — the exact phrasing rule 3a
  lists as `IMPROVES_ON`. `REPLACES` is a supersession trigger, and
  `_gate_replaces_selection`'s `_SELECTION_RE` does not match that wording,
  so the wrong edge landed unrepaired and could retire a live memory.
- **`service` exemplified `'PostgreSQL'` while `database` exemplified
  `'Postgres'`** on adjacent lines under a "pick the FIRST type that fits"
  rule. Phase-4 dedup is type-constrained, so unknown hosted datastores
  split into permanent duplicate nodes. The tiebreak is now stated.
- **Diet: -2,923 chars.** Example 4's notes, Example 5's prose notes,
  rule 2a's worked failure-mode narrative, a duplicated placeholder
  warning, and rule 10's restatement of 9c-soft.

**Example 5's demonstration was deliberately kept.** The review recommended
deleting it outright, which was the single largest item on its list. It is
the only place the star-shape relation failure is *shown* rather than
described, and at 39 relations this bench cannot reliably detect that
regression — so the saving was not worth a defect the instrument cannot
see. Only its prose notes were compressed. The bound in
`test_prompt_consistency.py` is 33,000 rather than the 27,000 originally
planned, for the same reason: the backstopped targets total ~6,600 chars,
and the rest would have had to come from rules `extraction_clean` does not
backstop.

### Artefacts

- `docs/planning/analyses/2026-08-27-prompt-review-central.md` — the seven
  prompts in `app/services/prompt.py`.
- `docs/planning/analyses/2026-08-27-prompt-review-scattered.md` — the
  eleven inline prompts held by individual services.
- `docs/superpowers/plans/2026-08-27-prompt-optimization.md` — the plan,
  including the two errors it contained.

### The two invalidated caches, both repaid

A prompt change invalidates more than the F1 bench cache, exactly as the
T1.17 entry above records. Both were re-recorded live before this work
merged:

- **The harvest fixture** (`scripts/benchlib/tests/harvest_l2_cache_fixture`)
  went red at `live_calls=190` against an expected 0. Regenerated: 213 new
  entries, 231 facts, capacity 924. The 595 pre-existing entries are kept,
  not pruned — a fixture holding only the 213 fresh ones still makes 22 live
  calls, so the older set is not all dead, and pruning by mtime would have
  left a fixture that looked warm while quietly failing 22 calls.
- **The retrieval eval's ingest cache**: re-ingested live at 188 calls. The
  retrieval arm is **unchanged** — MRR 0.8368, hit@10 0.8235, identical to
  the three prior runs — so the graph the new prompt builds retrieves the
  same. Recorded in `docs/eval/2026-08-27-retrieval-eval.md`.

  One caveat on that report: the full-context arm made **zero** live calls
  and its numbers are replayed from an older generation, because its calls
  carry no extraction prompt and its cache stayed valid. Its 0.9052 is not
  a measurement of this prompt and must not be read as a recovery from the
  0.8905 measured live earlier the same day.

`./scripts/gate.sh --full` is green on this branch: floor + retrieval eval
+ API e2e + Playwright + port hygiene.
