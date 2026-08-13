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
| G-C | L2 → deriver; Phase 2 exit | **open** (re-measured 2026-08-08 under the ratified veto shape: still not evaluable — under-powered on every probe, unchanged. The audit's arms were **re-derived, not merely re-run**: the machine arm is now judge-free, so the G-C→G-D critical-path edge recorded 2026-08-07 no longer holds as written — see "G-C re-measure". No promotion record minted) | — | T2.111 — this file, "G-C re-measure"; T2.40 — "G-C verdict"; `docs/eval/2026-08-0{7,8}-promotion-metrics.md`; `docs/eval/2026-08-07-t2.40-gc-evidence/` |
| G-D | L2 → L3 | **open — the final sanctioned attempt is spent** (2026-08-12, T2.114, owner-ruled `gpt-5.5`: NOT CLEARED — contradiction-**recall** 0.8875 pooled / 0.8500 Rule B, both vs 0.95; the other six bar readings pass. The stopping rule has fired: no further model is tried on pair set `4975c5cc`, and the remaining moves — a new gold or a bar argument — must stand on grounds that do not cite this result. Prior runs: 0.9375 deepseek on the resized gold (2026-08-10, missed by one pair), 0.9125/0.9200 gpt-5.5 on the grown gold (2026-08-08); under the retired single-precision gate: 0.7937 deepseek / 0.8814 gpt-5.5 vs 0.95 — see "G-D resolution" for why that gate was incoherent) | — | T2.114 — this file, "G-D final attempt"; T2.41 — "G-D re-measure", "G-D verdict", "G-D resolution"; `docs/eval/2026-08-12-judge-qualification-fd39e7b2.md`, `docs/eval/2026-08-10-judge-qualification-4d886440.md`, `docs/eval/2026-08-08-judge-qualification-{4d886440,1bb9d9ba,fd39e7b2}.md` |
| G-E | L3 → F7 | **open** (both bars stated 2026-08-11 by derivation and owner-ratified before any coverage number exists anywhere: runtime threshold **0.95**, corpus share **0.90**. Nothing is measured until T3.24's runner reads production — see "G-E") | — | — |
| G-F | core → H1 | **open** | — | — |
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

| Probe | Bar | Measured | Artifact | Verdict |
|---|---|---|---|---|
| Retrieval eval stable | — | — | — | — |
| Promotion metrics stable | — | — | — | — |
| Faithfulness (span-support coverage) on block-span entailment gold | Defined in TH1.01 **before** build | — | — | — |
| Maintainer appetite | Explicitly stated | — | — | — |

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
