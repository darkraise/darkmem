# G-C evidence run — T2.131 corpus, pass 2 (simulated capture clock)

Verbatim stdout of:

```
BENCH_DATABASE_URL=...darkmem_bench_t2131sim python scripts/benchlib/run_gc_evidence.py --corpus promotion
```

Run 2026-08-16, replayed from the extraction cache pass 1 wrote: `ingest live_calls: 0`. The one simulated step is the capture-time provenance stamp, which is what lets the `time_gap` gate fire; comparing this against pass 1 is what makes that dependency auditable rather than asserted.

```text
bench_db: darkmem_bench_t2131sim
corpus: promotion (849 captures, sha256 78dbc4c5c8756dcd)
ingest live_calls: 0
embedder fingerprint: qwen3-embedding:0.6b|1024
lift: {'ticks': 2, 'facts_created': 607, 'sources_added': 925, 'stalled_candidates': 0, 'salience_min_asserting_memories': 1}
wave 1 recompute (before wave 2 landed): {'ticks': 15, 'recomputed': 1047, 'transitions': 392}
wave 2: 2 captures, lift {'ticks': 2, 'facts_created': 1, 'sources_added': 2, 'stalled_candidates': 0, 'salience_min_asserting_memories': 1}
capture-time provenance stamped (SIMULATED CLOCK): 927 rows
repo assertions: {'payments-gateway': {'repo_id': '0e77b03d-e6fe-5ed8-8794-cf012c08bb22', 'entities': 103, 'relations': 102, 'internal_imports': 0, 'skipped_by_language': {}}, 'fraud-scoring': {'repo_id': '82b20960-8501-5c37-81c6-c416c10511c2', 'entities': 71, 'relations': 70, 'internal_imports': 0, 'skipped_by_language': {}}, 'merchant-portal': {'repo_id': '8705be9d-dabe-50fb-9670-2a9b5c735a0d', 'entities': 71, 'relations': 70, 'internal_imports': 0, 'skipped_by_language': {}}, 'dispute-workflow': {'repo_id': '8aa5c652-923a-53f4-8ac5-eb60cdde5947', 'entities': 67, 'relations': 66, 'internal_imports': 0, 'skipped_by_language': {}}, 'treasury-sync': {'repo_id': '66c0559d-0e86-5d89-8433-3cd05bae529f', 'entities': 67, 'relations': 66, 'internal_imports': 0, 'skipped_by_language': {}}, 'notification-relay': {'repo_id': '378bd66b-6987-5965-897d-f88a5792be79', 'entities': 64, 'relations': 63, 'internal_imports': 0, 'skipped_by_language': {}}}
code lift: {'ticks': 2, 'facts_created': 74, 'sources_added': 437}
facts minted through the shipping lift: 682
diversity claims authored per repo: {'dispute-workflow': 51, 'fraud-scoring': 56, 'merchant-portal': 55, 'notification-relay': 50, 'payments-gateway': 101, 'treasury-sync': 52}
== twin (rule 2) ==
  wall clock: 45.84s
  live model calls: 0
  extraction: live=0 paid_prompt=0 paid_completion=0 replayed_prompt=8374349 replayed_completion=117510 cache_known=849 cache_unknown=0 live_unknown=0
note: wave 1 (847 captures) was recomputed to convergence before wave 2 (2 captures) was ingested; the dispute wave 2 arms is owed to the ticks that follow
recompute tick 1: drained 2 events, recomputed 2 facts, 2 transitions; slow arm skipped (scanned 0, healed 0)
recompute tick 2: drained 0 events, recomputed 0 facts, 0 transitions; slow arm skipped (scanned 0, healed 0)
recompute: 2 ticks, 2 facts recomputed, 2 journaled transitions

== promotions journaled, read back from `events` by SQL ==
  gate_fired=diversity: 363 promote events over 363 distinct facts
  gate_fired=none: 145 promote events over 145 distinct facts
  gate_fired=time_gap: 20 promote events over 20 distinct facts
  total distinct facts promoted: 528

== fact census (project, status, distinct origins, kinds) ==
  atlas     candidate     origins=1 kinds=1 provenance_rows=1 -> 2 facts
  atlas     corroborated  origins=2 kinds=1 provenance_rows=2 -> 18 facts
  basalt    candidate     origins=1 kinds=1 provenance_rows=1 -> 6 facts
  basalt    corroborated  origins=3 kinds=1 provenance_rows=3 -> 21 facts
  default   candidate     origins=1 kinds=1 provenance_rows=1 -> 48 facts
  default   corroborated  origins=1 kinds=1 provenance_rows=1 -> 74 facts
  default   corroborated  origins=2 kinds=1 provenance_rows=4 -> 1 facts
  default   corroborated  origins=2 kinds=2 provenance_rows=2 -> 363 facts
  default   corroborated  origins=3 kinds=1 provenance_rows=3 -> 1 facts
  foundry   candidate     origins=1 kinds=1 provenance_rows=1 -> 3 facts
  foundry   corroborated  origins=3 kinds=1 provenance_rows=3 -> 23 facts
  harbor    candidate     origins=1 kinds=1 provenance_rows=1 -> 2 facts
  harbor    corroborated  origins=3 kinds=1 provenance_rows=3 -> 23 facts
  ledger    candidate     origins=1 kinds=1 provenance_rows=1 -> 6 facts
  ledger    candidate     origins=1 kinds=1 provenance_rows=3 -> 1 facts
  ledger    candidate     origins=2 kinds=1 provenance_rows=2 -> 1 facts
  ledger    corroborated  origins=3 kinds=1 provenance_rows=3 -> 32 facts
  orchard   candidate     origins=1 kinds=1 provenance_rows=1 -> 2 facts
  orchard   corroborated  origins=3 kinds=1 provenance_rows=3 -> 22 facts
  scheduler candidate     origins=3 kinds=1 provenance_rows=3 -> 1 facts
  signal    candidate     origins=1 kinds=1 provenance_rows=1 -> 7 facts
  signal    corroborated  origins=3 kinds=1 provenance_rows=3 -> 23 facts
  warehouse disputed      origins=1 kinds=1 provenance_rows=1 -> 1 facts
  warehouse disputed      origins=4 kinds=1 provenance_rows=4 -> 1 facts

== the designed refusals (echo, under-sourced) ==
  ledger: ledger-exports USES avro -> candidate (origins=2, provenance_rows=2)
  ledger: ledger-core USES cassandra -> candidate (origins=1, provenance_rows=3)

== the armed veto: disputes the detector actually produced ==
  warehouse: hive REPLACES trino -> disputed by rule=inverse_replacement against [trino REPLACES hive], witness=claude-code:aa10b3c7, corroborated_first=False
  warehouse: trino REPLACES hive -> disputed by rule=inverse_replacement against [hive REPLACES trino], witness=codex:ee5c67b3, corroborated_first=True
  disputes after a journaled corroboration (the audit's numerator): 1

== the withheld promotion: supersession-blocked holds the ladder journaled ==
  scheduler: dagster REPLACES oozie -> held at candidate (1 supersession_blocked hold event(s))
  supersession_blocked hold events journaled: 1
  superseded memories by project (arming project must read 0):
    atlas     superseded=0 of 36
    basalt    superseded=0 of 66
    default   superseded=0 of 365
    foundry   superseded=0 of 69
    harbor    superseded=0 of 69
    ledger    superseded=0 of 101
    orchard   superseded=0 of 66
    scheduler superseded=2 of 3
    signal    superseded=0 of 69
    warehouse superseded=0 of 5

== diversity reconciliation, per repository (authored vs promoted) ==
  dispute-workflow         authored=51   promoted=51   shortfall=0
  fraud-scoring            authored=56   promoted=56   shortfall=0
  merchant-portal          authored=55   promoted=57   shortfall=-2
  notification-relay       authored=50   promoted=50   shortfall=0
  payments-gateway         authored=101  promoted=99   shortfall=2
  treasury-sync            authored=52   promoted=52   shortfall=0
  total authored=365 promoted=365 conversion=1.0000

# Promotion metrics — 2026-05-18 to 2026-08-16

- database: `localhost:5433/darkmem_bench_t2131sim` (read-only)
- window: `2026-05-18T14:32:35.629962+00:00` .. `2026-08-16T14:32:35.629962+00:00`
- schema present: True
- `verified` payloads validated (T2.60 / unknown-vocabulary guard): 531
- under-powered threshold: < 5 observations

This is a measurement, not a verdict: no bar is stated or judged here (T2.40's role). Every rate below carries its denominator; a slice below the under-powered threshold is labelled, never read as a plain percentage.

**Units: every promotion-rate figure below is per-transition (per journaled `verified` event), not per-fact.** Doc 17 §5.1 states the metric as `(facts promoted) / (eligible candidate facts)`; a fact that exits `candidate` more than once inside the window (e.g. promote, later demote, later re-promote) contributes one row per transition to both promoted and eligible here, not one row per fact. The false-promotion audit below is the one number in this report that IS de-duplicated to distinct facts (`COUNT(DISTINCT object_id)`), matching doc 17's own wording for that metric — do not read the two counting conventions as consistent with each other.

## Promotion rate — by which N-fired gate (`gate_fired`)

| gate_fired | promoted | blocked | eligible | rate |
|---|---|---|---|---|
| diversity | 363 | 0 | 363 | 1.000 |
| none | 145 | 1 | 146 | 0.993 |
| time_gap | 20 | 0 | 20 | 1.000 |

## Promotion rate — by source-kind diversity

**Caveat: the `diverse` bucket is not equivalent to "the diversity gate fired".** It buckets on whether the payload's `source_kinds` list (the union of kinds across every origin that ever asserted the fact, including a single origin whose own rows span two kinds) contains more than one distinct value. The ladder's actual diversity gate (`OriginProfile.kinds_are_diverse`) is stricter: it requires **two distinct, attributable origins** that differ in kind, and returns `False` outright for a lone origin regardless of how many kinds that one origin spans. So a fact asserted by exactly one origin under two kinds slices as `diverse` here without ever having lowered N — this is a deliberately independent cut (per doc 17 §5.1's two-slice-axes instruction), not a proxy for `gate_fired = 'diversity'`; use the gate_fired table above for that question.

| bucket | promoted | blocked | eligible | rate |
|---|---|---|---|---|
| diverse | 363 | 0 | 363 | 1.000 |
| homogeneous | 165 | 1 | 166 | 0.994 |

## False-promotion audit

Count of DISTINCT corroborated facts later disputed or human-rejected (doc 17 §5.1). Sources: `events` self-join for the disputed half (T2.06's exact SQL, tuple-compared).

**The human-rejected half is live as of T2.63.** It reads the `human_verdict` journal, not `review_state` -- that column is pure queue-membership (T2.62: only `open` is writable, cleared to NULL on resolution), so it could never carry a verdict and this count read 0 forever while its own tripwire could not fire. A 0 here is now a measurement, not an absence -- but note the only human verb reachable today is rejection; ratify is T2.05's and re-ground/edit have no owner, so this counts rejections rather than all adjudication.

- corroborations in window: 528
- later disputed: 1
- later human-rejected: 0
- DISTINCT facts in either arm: 1
- false-promotion rate (point estimate): 0.0019
- corroborated facts later expired (R2 companion): 0

**The scored rule is the confidence bound, not the rate above (T2.132).**

- **SCORED** — 95% upper confidence bound on the TRUE rate: **0.008953** against bar 0.01 → CLEARS
- P(this window passes | the system's true rate is exactly the bar):
    - under `rate < bar` (superseded 2026-08-15): **0.5667**
    - under `upper bound < bar` (scored): **0.0314**
- corroborations needed for the bound to clear at 1 observed: **473** (have 528)

**A point estimate below the bar is not evidence the system is below the bar.** Comparing an observed rate to the bar it is centred on is a coin flip at the boundary *at every sample size* — measured 0.56 at n = 149 and 0.49 at n = 10000, so more corroborations do not repair it. The upper-bound line answers the gate's actual question and has been the scored one since the owner's call of 2026-08-15; it is strictly the more conservative of the two, so the switch can only refuse windows the old rule cleared, never the reverse.

**The last line is `promotion_bars` ruling R2's companion, and the rate above must not be quoted without it.** An entity-merge fact fold keeps one row's id and retires the other, so a corroboration and a later dispute can land on two ids that the audit's join can never bring together — the audit then undercounts, the one direction it may not err in silently. A non-zero count here caps what a zero rate claims. It is an upper bound on folds by construction: human adjudication and provenance withdrawal expire facts too, and the journal carries no discriminator, so this counts every expiry after an in-window corroboration rather than narrowing the cap on a guess.

The three counts above do not sum: a fact the human rejects is usually one the queue served them *because* it was disputed, so it appears in both arms. doc 17 §5.1 counts facts, so the rate divides the DISTINCT union — summing the arms reported 200% off a single fact.

== journal completeness (promotion_bars.JOURNAL_COMPLETENESS_SQL) ==
facts: 682; born-rung carve-out: 74; violations: 0

== bars in force (promotion_bars, committed before any measurement) ==
the measured database carries no `config` row for any G-C bar and no `promotion_bar_licences` row: every bar below is its committed default, unmoved.
bar                                 committed  effective  provenance
verification_false_promotion_bar    0.01       0.01       no config row; the committed bar stands
false_promotion_min_corroborations  20         20         no config row; the committed bar stands
promotion_rate_floor                0.5        0.5        no config row; the committed bar stands
promotion_rate_min_eligible         5          5          no config row; the committed bar stands
promotion_rate_min_promotions       1          1          no config row; the committed bar stands
promotion_journal_completeness_bar  1          1          no config row; the committed bar stands
note: promotion_journal_completeness_bar is read by no predicate today (the 100 % bar is spelled as zero unexplained rows), so its row and its clamp are prophylactic, not a live protection.

== pre-stated verdicts (promotion_bars, committed before this run) ==
by gate_fired: decidable=True (eligible per bucket: [363, 146, 20], promotions: 528)
  bucket diversity: powered=True clears=True
  bucket none: powered=True clears=True
  bucket time_gap: powered=True clears=True
by diversity: decidable=True (eligible per bucket: [363, 166], promotions: 528)
  bucket diverse: powered=True clears=True
  bucket homogeneous: powered=True clears=True
false-promotion audit: decidable=True clears=True (corroborations: 528, false promotions: 1, scored bound: 0.008953 at 95% confidence, point estimate: 0.001893939393939394, R2 companion -- corroborated facts later expired: 0)
journal completeness: clears=True over 682 facts (74 carve-out rows) -- vacuous unless transitions occurred
```
