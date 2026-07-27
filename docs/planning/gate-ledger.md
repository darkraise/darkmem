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
| G-A | Phase 0 → 1 | **open** | — | — |
| G-B | Phase 1 → 2 | **open** | — | — |
| G-C | L2 → deriver; Phase 2 exit | **open** | — | — |
| G-D | L2 → L3 | **open** | — | — |
| G-E | L3 → F7 | **open** | — | — |
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
| Extraction F1 parity with the recorded baseline | Within the T0.05 tolerance | — | n/a | — | — |
| Retrieval eval vs full-context baseline | Reported with twin; no silent regression | — | p95 —, tokens — | — | — |
| Isolation probe: unlabelled cross-project or superseded rows, **every** channel | **Exactly 0** | — | n/a | — | — |

**Requirement recorded by T0.05:** the runner producing this gate's live F1
re-record must capture and record response metadata (the served `model` string
and any vendor system fingerprint) alongside its cache. The T0.05 baseline's
cache carries none, so model identity is only checkable from the G-B side; a
shortfall attributed to a vendor-side model update is admissible only with that
metadata recorded (see the "same model" gap under G-A).

**Isolation probe detail** (T1.35) — a single leaked row fails the gate:

| Channel | Cross-project leaks | Superseded leaks | Verdict |
|---|---|---|---|
| Semantic | — | — | — |
| Keyword | — | — | — |
| Graph | — | — | — |
| `memory_reason` | — | — | — |
| Code search | — | — | — |

---

## G-C — L2 → deriver; Phase 2 exit

**Owning task:** T2.40. **Bar lives in:** `config` rows. **Metrics computed from the
`events` journal by SQL** — an unjournaled transition is an unmeasurable one.

| Probe | Bar | Measured | Artifact | Verdict |
|---|---|---|---|---|
| Promotion rate `(promoted / eligible)`, sliced by source-kind diversity | — | — | — | — |
| Promotion rate, sliced by which N fired | — | — | — | — |
| False-promotion audit (corroborated later disputed or human-rejected) | Under stated bar | — | — | — |
| Every ladder transition journaled | 100% | — | — | — |

**Consequence of a miss:** the code-deriver lane (T2.27–T2.28) stays closed. The deriver
mints facts born `corroborated`; shipping it over an unproven ladder would put unverified
assertions into the vault at the ladder's second rung.

---

## G-D — L2 → L3

**Owning task:** T2.41. **Bar lives in:** `config` + the gold set.

| Probe | Bar | Measured | Artifact | Verdict |
|---|---|---|---|---|
| `verification` judge precision on labelled entailment gold | — | — | — | — |
| `verification` judge recall on labelled entailment gold | — | — | — | — |

**Gold set:** built in T2.25, **before** the judge, so the judge cannot be tuned to its
own test. Material comes from running `article_synthesis` in a labelled non-shipping
mode against `darkmem_bench`, plus hand-authored claim/fact pairs — **not** from real
Phase-3 drafts, which do not exist until after this gate clears.

**Consequence of a miss:** E3 stays closed. Below the bar, no L3 article ships as grounded —
enforced in code (T3.03), not by policy.

---

## G-E — L3 → F7

**Owning task:** T3.22. **Bar lives in:** `config`.

Measured by T3.24's runner. The production read is the one sanctioned exception to
"nothing automated touches `darkmem`" — it is **read-only** and may never write.

| Probe | Bar | Measured | Artifact | Verdict |
|---|---|---|---|---|
| L3 shipped | Articles live in production | — | — | — |
| Per-article claim-support coverage **distribution** above the runtime threshold | — | — | — | — |

**A distribution, not a mean.** One well-covered article does not clear this gate; the
question is whether coverage holds across the corpus in production.

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
| — | — | — | — | — | — | — |
