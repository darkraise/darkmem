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
| Isolation probe: unlabelled cross-project or superseded rows, **every** channel | **Exactly 0** | **10** (2026-07-28, T1.35), then **0** (2026-07-28, T1.35a) | n/a (deterministic, zero model calls) | `backend/scripts/benchlib/run_isolation_probe.py` (output below) | **PASS on the re-measurement; the 10 stands recorded** |

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
