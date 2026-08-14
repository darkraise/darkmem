# T2.129 follow-on — restoring the supersession-blocked hold's reachability

**Date:** 2026-08-14. **Branch:** `feat/t2.129-gc-corpus`.
**Corpus sha256:** `69dbb717b04761671ec196ef62175407957764702fcb22f0416b23d29539b354`
(`69dbb717b0476167` in the runner's 16-char spelling) — a new corpus, not a
re-run of pass 2's `2840651b597da347`.
**Database:** `darkmem_bench_t2129hold`, created for this lane alone.

This lane built the change and may not certify it as gate evidence. The
independent evidence re-run T2.129's done-when owes remains owed and is not
discharged here.

## 1. The problem

Pass 2's repair added a `validate_arming_design` clause refusing any arming
capture inside the supersession window. That clause is what lets the armed
fact reach the false-promotion audit's numerator — and, as the independent
probe found (ledger, "G-C arming, passes 1 and 2"), it also makes the
`supersession_blocked` hold **structurally unreachable in the arming groups
for every admissible future corpus**. The 2026-08-13 owner ruling made
`blocked ≡ 0` reachable "until a veto **or** a supersession-blocked hold
actually fires in a measured window"; the repair delivered the veto arm and
foreclosed the other.

## 2. The design: a `blocked_hold` group in its own project

Three sessions in a fresh project (`scheduler`) assert one replacement
(`dagster REPLACES oozie`), deliberately dated **inside** the window. Ingest
retires each capture under the next (`detect_supersessions`, same-project,
window-anchored at ingest wall-clock), the fact still meets its count
(`fact_lift`'s `asserted` CTE joins `memories` with no status filter), and
`decide` journals the meets-bar-but-held outcome with
`supersession_blocked=true` — the exact event `_PROMOTION_RATE_BY_GATE_SQL`
counts into `blocked`. The arming groups stay guarded: the window clause
iterates `subject_entries + counterpart_entries` only, and the change is
purely additive to it.

**Dates are spelled relative to the run clock** (`now-<N>d`, resolved at
load): "inside the look-back window at ingest" is a run-clock-relative
property that no absolute date can carry for longer than the window's width.
An absolute date in this group is a silent 90-day fuse — the corpus keeps
loading after the date recedes, supersession quietly stops firing, and
`blocked` returns to an unreachable 0 with no symptom. The loader therefore
refuses an absolute date inside the group and a relative date anywhere else,
and `validate_blocked_hold_design` is the mirror of the arming clause: one
claim, one direction, names disjoint from the arming pair, a project of its
own, inside the window against the run clock, distinct capture times.

### Door-reachability, verified rather than assumed

The probe's claim checks out in code, and it is the strongest argument for
this shape:

- `MemoryCreate` (`app/schemas/memory.py`) carries **no** `created_at`;
  production stamps it at ingest.
- `detect_supersessions` (`app/services/supersession.py`) anchors its window
  at `now or datetime.now(timezone.utc)`, and the pipeline call site omits
  `now`.
- Therefore three same-claim REPLACES captures days apart **cannot** all
  survive `active` through any capture door: each ingest retires the
  previous. That is pass 1's configuration — and it is the `blocked_hold`
  group's. Pass 2's arming state (three same-claim captures all `active`)
  exists only because the harness backdates attribute-side; the
  `blocked_hold` group is the **only** group in this corpus whose measured
  database state is reachable through a capture door with a real clock.

### Alternatives considered, and why this one wins

**(b) A waivable window clause** (per-entry marker exempting an arming
capture). Rejected: it weakens the guard by construction — pass 1's silent
zero-numerator becomes a one-line edit away again, and the protection
degrades from a structural refusal to a convention. It also delivers
either/or, not both-at-once: a waived arming corpus reproduces pass 1
(numerator 0, holds firing); an unwaived one reproduces pass 2 (numerator 1,
holds unreachable). The ruling's two arms would still never fire in one
measured window. The task's hard constraint forbids this direction anyway.

**(c) Leave as-is; treat pass 1's preserved database as standing evidence.**
Rejected on three grounds. First, reproducibility: pass 1's evidence is not
reproducible from committed state — the committed validator refuses its
corpus, and after ~2026-10-18 even deleting the validator would not help,
because the pass-1 dates exit the window against a live clock. A preserved
database on one host is exactly the artifact class this ledger treats as
second-tier ("preserved but no longer reproducible"). Second, the ruling's
arms have never both fired in **one** measured window: pass 1 had holds and
no numerator; pass 2 the numerator and no holds. Third, regression
coverage: under (c) every admissible future corpus reads `blocked = 0`
forever, so a regression in the hold's journalling (the T2.60 shape the
metrics SQL depends on) would be invisible to every future G-C run.

**(a) The separate group** is additive (no existing predicate moves), makes
both arms fire in one measured window, is the production-faithful half of
the corpus (door-reachable, above), and keeps each demonstration readable
independently (own project, disjoint names, project-scoped supersession and
detector).

### Costs, stated

- The corpus is no longer a fully absolute timeline: one group's dates
  resolve against the run clock, so two runs on different days produce
  byte-different `memories.created_at` values in the `scheduler` project.
  The design properties (inside-window, span < 7 days, ordering) are
  invariant; the corpus sha is unchanged across runs. Note the corpus
  already ceased to be clock-independent when the arming window clause
  landed — that clause reads the live clock at every load.
- Three new contents mean the next evidence run makes live extraction calls
  (the cache is content-keyed). Disclosed below.
- The `blocked_hold` fact adds hold events to the `gate_fired=none` bucket's
  eligible set, lowering that bucket's rate slightly (pre-stated below);
  this is the same accounting pass 1 exhibited and is far above the 0.5
  floor.

## 3. Pre-registered expectations (written and committed before the run)

Everything the numerator path produced in pass 2 must reproduce unchanged:

1. Promotions journaled: **149** distinct facts, buckets
   diversity 98 / none 33 / time_gap 18 promoted.
2. False-promotion audit: corroborations **149**, later disputed **1**,
   rate **1/149 = 0.0067**, R2 companion 0; `decidable=True clears=True`.
3. The armed dispute: `trino REPLACES hive` disputed under
   `inverse_replacement`, `corroborated_first=True`; numerator **1**.
4. Arming project (`warehouse`): **0** superseded memories.

The restored arm, new in this window:

5. `scheduler` project: **exactly 2 of 3** memories `superseded` (each
   capture retired by the next-dated one; the newest survives `active`).
6. Fact `dagster REPLACES oozie` (project `scheduler`): final status
   `candidate`, origins = 3, never journaled `corroborated`, never
   promoted.
7. `supersession_blocked` hold events: **≥ 1** on that fact (the
   pre-registered pass condition), expected **exactly 1** — one eligible
   decision at k = 3 during wave-1 convergence; unlike pass 1's armed
   subject there is no wave-2 re-decision. If more than 1 appears, each
   extra must be explained from the journal as an additional eligible
   re-decision, not waved through.
8. Bucket accounting: `gate_fired=none` eligible = 33 + B where B is the
   hold-event count (expected 34), rate 33/34 = **0.971** under B = 1 —
   powered (≥ 5) and clearing (≥ 0.5). Eligible vector expected
   [98, 34, 18].
9. No bar, threshold or ladder predicate moves: the bars-in-force block
   must read "no config row; the committed bar stands" for every bar.
10. `live_calls` > 0 (three new contents; extraction via
    `deepseek-v4-flash`, embeddings via the LAN Ollama). Expected small
    (single digits). This run therefore re-exercises the live extraction
    path for the new group only; everything cached is vouched for by
    pass 1's live run, exactly as pass 2's caveat 1 recorded.

Total facts: expected 176 (175 + the one scheduler fact). Extraction
variance may mint additional one-origin `scheduler` candidates; they journal
nothing and change no verdict, and the census will show them if they exist.

**If the run misses any of 1–4, the guard was weakened and the change is
wrong. If it misses 5–7, the restored arm did not restore and the finding is
recorded red — the corpus moves, never a bar.**

## 4. Measured results

(Appended after the run; the section above is committed first.)

Run artifact: `bench-run.txt` in this directory. Database
`darkmem_bench_t2129hold`; run window
`2026-05-16T12:32:05Z .. 2026-08-14T12:32:05Z`; executed inside a systemd
scope capped at `MemoryMax=4G / MemorySwapMax=256M`.

**Correction, 2026-08-14 (found in controller verification, after this report
was written): that database no longer holds this run.** The harness suite was
run against the same database *after* the evidence run, and the DB-backed tests
reset the schema — so the verification step destroyed the state it was
verifying. `darkmem_bench_t2129hold` now holds two rows from a unit-test probe.
Anything in this report that reads as "the rows are there to inspect" is false;
`bench-run.txt` is the evidence, and it is intact. The lesson is the reason
runs are committed rather than left live: **an evidence database and a test
database must not be the same database**, and this lane used one name for both.

**Expectations 1–4 (the guard did not weaken): all hold, byte-for-byte
against pass 2.** Promotions 149 (98/33/18); audit corroborations 149,
later disputed 1, rate 0.006711, R2 companion 0, `decidable=True
clears=True`; `trino REPLACES hive` disputed under `inverse_replacement`
with `corroborated_first=True`, numerator 1; `warehouse` superseded = 0.

**Expectations 5–6 (the restored arm): hold.** `scheduler` superseded =
exactly 2 of 3; the fact `dagster REPLACES oozie` holds at `candidate` with
origins = 3, never journaled `corroborated`, never promoted; it is the only
`scheduler` fact in the census (no extraneous candidates).

**Expectation 7: the ≥ 1 pass condition holds; the point estimate was
wrong, and the extra is explained from the journal rather than waved
through.** Measured **2** `supersession_blocked` hold events, not 1. The
journal shows three `sources_changed` events for the fact, all stamped
`12:31:51.63` (one lift tick wrote all three sources), and two `verified`
holds 0.72 s apart (`12:31:58.47`, `12:31:59.18`), **both** `k=3 n=3
candidate → candidate blocked=true`. The recompute's fast arm drains events
in batches of `batch_size` = 100, and wave 1's lift produced ~260
`sources_changed` rows, so the fact's three events straddled a drain-batch
boundary and it was recomputed in two consecutive ticks — each eligible
blocked decision journals (per-transition units, the same accounting that
gave pass 1's armed subject two holds). No mystery transition, no second
fact. The pre-registration's derivation ("one eligible decision") assumed
the drain sees a fact's events in one tick, which the batch bound does not
promise. Recorded as a miss in the same spirit the ledger recorded the
pass-2 plan's one-hold-vs-two error.

**Expectation 8: holds in its parameterized form.** Bucket `none` eligible
= 33 + B with B = 2 → 35, rate 33/35 = 0.943, powered and clearing;
eligible vector [98, 35, 18] (the pre-stated point vector [98, 34, 18]
assumed B = 1).

**Expectations 9–10: hold.** Every bar reads "no config row; the committed
bar stands"; `live_calls` = 6 (the three new contents, extraction +
classification via `deepseek-v4-flash`; embeddings hit the LAN Ollama).
Total facts 176; journal completeness 0 violations over 176 facts.

## 5. What this achieves, and what it does not

Both arms the 2026-08-13 ruling names now fire in **one** measured window,
reproducible from committed state at any future run date: the veto arm
(1/149 with `corroborated_first=True`) and the supersession-blocked hold
(2 hold events, 2 superseded memories, fact held at `candidate`), each in
its own project, with the arming project's superseded count printed as 0 on
the same page.

It does **not** clear G-C, does not mint
`promotion_metrics_record.json`, and does not change what pass 2's caveats
said about power (the audit still cannot reject a system sitting at the
bar), about the one-fact numerator, or about authorship (the three new
contents' extraction is vouched for by this run alone, made by the group's
own author — the same single-live-run caveat as pass 1). The blocked-hold
demonstration is instrument-operability: the corpus was authored to be
held, so the 2 blocked events confirm design, not system behaviour. This
lane may not certify this run as gate evidence; the independent re-run
stands owed.

## 6. Suite status

- Harness suite (`pytest scripts/benchlib/tests`, own database
  `darkmem_bench_t2129hold`): **868 passed** (baseline 853 + 15 new).
  Earlier flaky failures during development were collisions with another
  process actively using the shared `darkmem_bench`; every run against this
  lane's own database is green.
- Backend floor (`python -m pytest -q`): **5364 passed, 2 failed,
  19 skipped**. Both failures are `tests/test_planning_docs.py`
  consistency checks about T2.129's own planning entries (no `progress.md`
  row; the Gate field's phrasing) — present at branch head `32a17469`,
  untouched by this change (its diff contains no `docs/planning` file),
  and owned by the controller's planning-docs lane.

### Mutation drills (the failing side, shown)

Two deliberate breaks of the new guard, each watched failing and then
restored to green:

- Window clause neutered (`outside = []` in `validate_blocked_hold_design`):
  `test_blocked_hold_clause_bites_on_a_date_outside_the_window` and
  `test_blocked_hold_clause_reads_its_bound_from_the_application` both
  FAILED; restored, all 14 blocked-hold tests pass.
- Group-existence refusal bypassed (early `return` on empty group):
  `test_blocked_hold_guard_refuses_a_corpus_without_the_group` FAILED;
  restored, full module 55 passed.
