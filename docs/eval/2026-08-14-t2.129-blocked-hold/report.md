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
