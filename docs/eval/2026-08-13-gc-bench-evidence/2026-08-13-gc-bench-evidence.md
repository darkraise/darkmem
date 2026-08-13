# G-C evidence run — the bench arm against T2.108's promotion corpus

**2026-08-13.** Adversarial gate probe, dispatched by
`docs/planning/briefs/2026-08-13-gc-bench-arm-evidence.md`. Charter: find the
reason G-C should **not** clear. Task lineage: T2.40 (gate owner task),
T2.108 (corpus), T2.111 (re-derived audit arms), T2.128 (bar-provenance
block, treated as untrusted and independently verified below).

Runner: `backend/scripts/benchlib/run_gc_evidence.py --corpus promotion`,
against `localhost:5433/darkmem_bench_gc` (created for this run; name passes
`assert_bench_db_allowed`). Two passes: the default (capture-time simulation
on) and `--no-capture-time-simulation`.

---

## Stated before the run

Written before either pass executed. Nothing below this section's end was
known when it was written.

### The bars in force

The six committed defaults in `backend/scripts/benchlib/promotion_bars.py`
(`PROMOTION_BAR_DEFAULTS`, stated 2026-08-07 before any G-C measurement,
pinned by `scripts/benchlib/tests/test_promotion_bars.py`):

| bar | committed value |
|---|---|
| `verification_false_promotion_bar` | 0.01 (strict `<`, ceiling) |
| `false_promotion_min_corroborations` | 20 |
| `promotion_rate_floor` | 0.5 |
| `promotion_rate_min_eligible` | 5 (= `UNDER_POWERED_THRESHOLD`, `Conservative.NEITHER`) |
| `promotion_rate_min_promotions` | 1 |
| `promotion_journal_completeness_bar` | 1.0 (read by no predicate; prophylactic) |

`darkmem_bench_gc` is created fresh and reset by the harness, so the expected
bar-block reading is the explicit no-rows sentence. The block is T2.128's and
its author flagged it as untrusted for this run; it is verified below against
the measured database's `config` table by independent SQL, not taken from its
own print-out.

### The decision rule

This run **cannot record CLEARED under any numeric outcome**, and that is
stated here, in advance, on grounds already on the record — not derived from
the numbers:

1. **The false-promotion audit's clear is vacuous on this corpus, and the
   ruling that binds it is unmade.** The 2026-08-07 Tier-2 amendment
   (M1 amendment log; verified on data by T2.108's adversarial review)
   records that `audit_clears(0.0, N≥20)` returns True while the audit's
   numerator is structurally zero, "cannot distinguish precision from
   inoperability", and that **the gate owner rules** before any verdict
   leans on it. No owner ruling exists. Re-derived under T2.109's ratified
   arm structure the vacuity *survives with updated reasons*, checked
   empirically below: `disputed_after`'s only producer is the deterministic
   detector, which needs a stored REPLACES-family edge (the corpus is
   expected to carry none — verified post-run) and whose `single_valued`
   sibling is disarmed; the LLM scan produces no disputes by construction
   any more and dead-ends on the unqualified judge anyway; `rejected_after`
   needs a human verdict, and no human adjudicates a bench database inside
   this run.
2. **The ledger's own route (b) has an unmet precondition.** The T2.40
   verdict's "What would evaluate this gate" clause (b) — the purpose-built
   corpus route this run is — carries "the same judge-qualification
   precondition for the audit". G-D is NOT CLEARED (T2.114 final attempt,
   contradiction-role bars missed; no qualification record for either role
   exists on this branch). The precondition is unmet.
3. **Probes 1–2 on an authored corpus partially measure the corpus design.**
   Route (b)'s stated caveat. A 1.000 promotion rate on a corpus authored to
   promote is evidence the machinery works, not evidence about the ladder's
   behaviour on organic capture.

What this run **can** produce: a NOT CLEARED verdict that, for the first
time, carries powered denominators — demonstrating the bench arm is operable
end-to-end — or a finding that outranks everything (a control-group
promotion, a completeness violation, a bar-block misreport), which would be
the headline instead.

Pre-stated expectations, from T2.108's recorded artifacts
(`docs/eval/2026-08-07-t2.108-promotion-corpus/`), against which drift is a
finding to explain rather than noise: 66 captures, sha256 `9c74f451b0cbfa14…`;
with simulation ~38 facts, 31 promotions (diversity 11 / none 10 / time_gap
10), audit corroborations 31, carve-out 1, violations 0; without simulation
the `time_gap` bucket empties and corroborations drop to 21 (≥ 20 still
decidable). The echo (`cassandra`, one origin behind three provenance rows)
and the under-sourced pair (`avro`, two same-kind origins inside a week)
stay `candidate`. **If either control promotes, the corpus or the ladder is
wrong and that outranks every other number in this run.** Unlike T2.108's
recorded run, the promotion cache is absent on this machine, so pass 1 makes
~66 live DeepSeek extraction calls (`deepseek-v4-flash`, the gate-fixed
model): `live_calls > 0` is expected and correct here, and extraction is
seeded (`sha256(content)`), so counts should land close to the reference but
are not guaranteed bit-identical.

### The question the brief requires answered before any verdict

**Can a bench-corpus run clear G-C at all, or only demonstrate operability?**

Answered from the documents, before the run, because it is a docs question
and not a numbers question:

- The two sentences the brief quotes do not contradict. "The production
  journal is the primary target" (driver docstring, ledger) states
  *preference*; "a purpose-built corpus was the only pre-cutover route to
  any verdict" (T2.108) states *availability* — doc 17 §11 sequences the
  cutover after these gates, so route (a) is unreachable until after the
  gate clears, and if only production could clear it the sequencing would
  deadlock. The ledger already resolves this: the T2.40 verdict's "What
  would evaluate this gate" names **both** routes, and route (b) is exactly
  this run's shape. Primary ≠ exclusive. So "a bench run can never clear
  G-C" is **not** what the record says, and no Tier-3 contradiction between
  those two sentences exists.
- But route (b) is *conditioned*, and the conditions are unmet today: the
  judge-qualification precondition for the audit (G-D open), and the
  unmade owner ruling on the audit's decidable-but-vacuous reading
  (2026-08-07 amendment). **So this run can only demonstrate operability,
  and the gate's definition does not have to change for that to be the
  honest verdict** — NOT CLEARED is recordable without touching the gate's
  terms. What *would* be Tier 3 is recording CLEARED from this run: that
  requires either ruling the vacuous audit acceptable (a gate-definition
  ruling only the owner can make) or asserting the judge precondition met
  (false). This report therefore records NOT CLEARED and escalates the one
  genuinely open question rather than settling it: **whether a route-(b)
  clear, once its conditions are met, licenses minting
  `promotion_metrics_record.json`** — i.e. lighting production badges on
  corpus-design evidence with the stated caveat, or whether the mint waits
  for route (a). Nothing in the ledger answers that, and it is the owner's.

---

## The run

*(Everything below was written after the passes executed.)*

Transcripts: `bench-run.txt` (pass 1, simulation on) and
`bench-run-no-simulation.txt` (pass 2) beside this file — the runner's full
stdout, untrimmed. Reproduce:

```
cd backend
DEEPSEEK_API_KEY=... \
BENCH_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench_gc \
  python scripts/benchlib/run_gc_evidence.py --corpus promotion [--no-capture-time-simulation]
```

### Headline numbers, both passes, denominators everywhere

Corpus `9c74f451b0cbfa14…` (unchanged since T2.108's commit `b33cee39`),
66 captures, fingerprint `qwen3-embedding:0.6b|1024`, 42 facts through the
shipping lift, window 2026-05-15 → 2026-08-13.

| Probe | Pass 1 (simulated clock) | Pass 2 (write time) |
|---|---|---|
| Rate by `gate_fired` | diversity 11/11, none 10/10, time_gap 10/10 — all powered (≥ 5), all clear 0.5 | diversity 11/11, none 10/10 — **time_gap bucket gone** |
| Rate by diversity | diverse 11/11, homogeneous 20/20 | diverse 11/11, homogeneous 10/10 |
| False-promotion audit | 31 corroborations (≥ 20, decidable), 0 disputed-after, 0 human-rejected, rate 0.0000; R2 fold companion **0** `expired` events | 21 corroborations — decidable by a **margin of one**; same zeros |
| Journal completeness | 42 facts, **1** born-rung carve-out, 0 violations | same |
| Controls (must stay `candidate`) | `ledger-exports USES avro` → candidate (2 origins, same kind, < 7 days); `ledger-core USES cassandra` → candidate (1 origin, 3 provenance rows) | identical |

Every pre-stated predicate printed True where its bucket was powered, in both
passes. **The verdict is still NOT CLEARED, per the decision rule stated
above** — see "Verdict".

### What the run demonstrated (the operability half)

- **The bench arm is operable end-to-end, powered for the first time.** Both
  recorded G-C measurements (T2.40, T2.111) read 0 eligible / 0 corroborations
  everywhere. This run put 31 journaled `promote` transitions through the
  shipping ladder — `run_recompute` drained 86 `sources_changed` events in one
  tick, slow arm ran, zero healed — and every probe finally has denominators.
- **Both designed refusals refused, for the designed reasons.** The echo held
  at one origin behind three provenance rows; the under-sourced pair held at
  k=2 same-kind origins inside a week against N=3. Independently confirmed by
  the census SQL (origins/kinds/provenance per fact).
- **Probe 4 is non-vacuous for the first time.** T2.40/T2.111 recorded
  "consistent but vacuous" (0 transitions, so 100 %-of-transitions was 0/0).
  Here 31 (21) transitions occurred and 0 rows are journal-unexplained, with
  exactly 1 carve-out row — `payments-gateway USES python`, code-only
  provenance, doc 10 §6's licence, named per R3 rather than absorbed. The
  claim is "100 % of counting-ladder transitions journaled, 1 born-rung row
  excluded", never a bare 100 %.
- **The gate-relevant structure survived a fully live re-extraction.**
  T2.108's recorded run was cache-served (`live_calls: 0`); this machine's
  promotion cache was empty, so pass 1 made **73 live round-trips**
  (seeded `deepseek-v4-flash` extraction for 66 captures plus embedding
  chunks; `CachingLLMOrchestrator` counts network round-trips). Extraction
  drifted — 42 facts against the reference's 38, lift 74 sources against 70 —
  and **every drifted fact landed as a single-origin `candidate`**: promotions
  are bucket-for-bucket identical (11/10/10), the audit and completeness
  numbers moved only by the drift's denominators, and both controls are
  byte-identical. Pass 2 replayed the now-warm cache (`live_calls: 0`).
- **The T2.128 bar block told the truth about the measured database.**
  Treated as untrusted per the dispatch (its author built it). Both passes
  printed the explicit no-rows sentence. Independent SQL against
  `darkmem_bench_gc.config`: **0 rows** for the six bar keys and
  `promotion_bar_licences`; the table's only rows are `feature_flags` and
  `verification_recompute_state`, both written by the harness's own flow,
  neither a bar. The printed committed/effective pairs match
  `PROMOTION_BAR_DEFAULTS` exactly. No misreport found.

### What the run confirmed against clearing (the adversarial half)

1. **The false-promotion audit's `decidable=True clears=True` is the vacuous
   reading the 2026-08-07 amendment predicted, now observed in a real gate
   run — and it survives T2.109's re-derived arm structure.** Verified on
   this run's data, not inferred:
   - `disputed_after`: its only producer is the deterministic detector;
     `SINGLE_VALUED_RELATIONS` is empty (`contradiction_veto.py:161`) and
     the measured database holds **0** REPLACES/IMPROVES_ON/BUILDS_ON rows
     in `entity_relations` (SQL, post-run), so `inverse_replacement` could
     not arm. The event journal carries only `sources_changed` (86),
     `extracted` (66), `verified` (21 in the persisted pass-2 state; 31 in
     pass 1's transcript) — every `verified` outcome is `promote`.
   - `rejected_after`: **0** `human_verdict` events — no human adjudicates a
     bench database inside a harness run, structurally.
   - The Tier-C LLM scan never ran, would dead-end on the unqualified judge
     (no role's qualification record exists on this branch), and since
     T2.109 could not produce a dispute even if qualified — its verdict
     rides `contradiction_suspected`, held inert by `decide`.
   So the zero numerator is inoperability, not measured precision, exactly
   as recorded. The owner ruling the amendment demands is still unmade, and
   this run is not entitled to make it.
2. **A third of the promotion evidence rests on the simulated clock, and the
   audit's decidability nearly does.** The 74 stamped rows cover all
   memory-kind provenance, but the A/B diff shows exactly one bucket rests
   on the simulation: `time_gap` (10 of 31 promotions). Without it the
   audit's denominator falls to 21 against the 20 floor — decidable by one
   corroboration. Any single-claim regression (extraction drift dropping one
   `none`-group fact, a corpus edit) flips the unsimulated pass to
   under-powered. The two passes agree on every predicate today, so the
   difference is not a verdict change — but the margin is one, and a future
   reader should know it.
3. **Probes 1–2 measure the corpus design in part.** Rate 1.000 in every
   powered bucket is what a corpus authored to promote produces when the
   machinery works. Route (b)'s stated caveat applies in full: this is
   evidence of mechanism, weak evidence about organic behaviour.
4. **`blocked ≡ 0` remains data-precluded** (vacuity clause 2): no veto
   fired, no supersession-blocked hold occurred, so `slice_clears`' failing
   direction was again unreachable. Same standing as T2.111 recorded — live
   in principle, untested by this corpus.

### Twin (rule 2)

Pass 1: **35.9 s wall**, 73 live LLM round-trips (deepseek-v4-flash
extraction + LAN Ollama embeddings). Pass 2: **14.6 s wall**, 0 live calls.
Every metric is SQL; the recompute converged in 2 ticks both times.
**Token counts are not measurable from this harness**: the cache stores
response text only and the runner prints no usage — recorded as a gap
against the twin rule for a future powered run, not silently omitted.

### Verdict

**NOT CLEARED — the bench arm is operable and powered, and the gate stays
open.** No numeric outcome of this run could have cleared it (stated before
the run): the false-promotion audit's clear is vacuous with all three
numerator producers verified dark, the owner ruling on that vacuity
(2026-08-07 amendment) is unmade, and the ledger route (b)'s
judge-qualification precondition (G-D, open) is unmet. `promotion_metrics_record.json`
was not minted; the deriver-lane consequence is unchanged; every promoted or
born badge keeps serving as `candidate` with `verification_unmeasured`.

**The Tier-3 question, answered:** a bench run *can* be a route to a G-C
verdict — the ledger's own route (b) says so, and doc 17 §11's sequencing
(cutover after the gates) makes it the only pre-cutover route, so "primary
target" (production) and "only pre-cutover route" (bench) do not contradict.
No gate-definition change is needed to record today's NOT CLEARED. What
would take a gate-definition act is recording CLEARED from this arm, and
that is escalated, not settled here. **Escalation to the gate owner, three
items:**

1. Rule on the 2026-08-07 vacuity amendment: what makes a zero-numerator
   audit *measured* rather than inoperable? (T2.108's review already showed
   no corpus in the 20–99 corroboration band can be both operable-numerator
   and passing under the strict 1 % bar — one genuine designed dispute
   breaches it — so the answer cannot be "add a dispute to the corpus"
   without also growing it past 100 corroborations, and the defect
   attributes to the bar.)
2. State whether a route-(b) clear, once its conditions are met, licenses
   minting `promotion_metrics_record.json` — production badges lighting on
   corpus-design evidence with the stated caveat — or whether the mint
   waits for a route-(a) production window.
3. If the bench route is to become clearable, decide the concrete arming
   path for the audit's machine arm: a corpus extension carrying a stored
   REPLACES-family edge would let `inverse_replacement` dispute judge-free
   (no G-D dependency), at the cost of item 1's band problem; the
   human arm needs G-D plus a reviewer, which no harness run can supply.

### Hygiene

`darkmem_bench_gc` created for this run and left in place (bench databases
are the harness's to reset; the name passes `assert_bench_db_allowed`). The
promotion cache under `backend/scripts/benchlib/promotion/cache/` is now
warm (188 files, gitignored). No process left running; the production
`darkmem` database was not touched by any command in this run.
