# E2 delta review — claim honesty and measurement integrity (2026-08-09)

**Range:** `c510e8ae..HEAD` (`feat/e2-truth-core`; HEAD moved from `beaefb4b` to `3f5da2ad`
during this review — the extra commit is a docs-only refresh of
`docs/eval/2026-08-09-retrieval-eval.md` by the in-flight gate run, verified report-only,
and is covered by this verdict). **Lens:** every sentence the delta adds is a claim; find
the ones whose evidence does not exist, is weaker than stated, or has been inverted.
**Method:** verified against shipped code with `file:line`; four mutation drills re-derived
(snapshot → mutate → scoped pytest → restore → `git status` clean after each); which checks
were re-run versus inherited is listed at the end.

**Verdict up front:** the fix wave delivers what it claims almost everywhere — every
mutation-evidence claim I re-derived was true, both gate-arm changes are honest, and the
2026-08-08 Critical is closed. One task in the delta (T2.112) claims more than it shipped:
the suspicion reaches the wire and dies at the screen, the same defect shape the same delta
just fixed for `label_suppressed`. That, plus two cheap siblings, is one small fix wave —
no re-architecture.

---

## Part 1 — verdicts on the 2026-08-08 findings

### Claim-honesty review

| Finding | Verdict | Evidence |
|---|---|---|
| **C-1** (Critical) — demo articles served in real mode | **ADDRESSED** | `articles-tab.tsx:80` (`DEMO ? demoArticles : NO_ARTICLES`), `knowledge_.articles_.$articleId.tsx:136`, nav gated at `_authenticated.tsx:60-62`; route stays reachable and falls to the honest empty state whose copy names the open gate. Guard `articles-tab.real.test.tsx` runs and passes (re-run, 6/6 with the suppression tests). The honesty e2e is no conflict: its "both modes" are simple/advanced detail levels with DEMO on. Mutation claim in `90395a20` inherited (structure verified by read). |
| **I-1** — suppression marker dies at the screen | **PARTIALLY ADDRESSED** | `SuppressedBadge` (`fact-parts.tsx:111`) rendered on the facts tab (`facts-tab.tsx:71`) and fact detail (`fact-detail.tsx:344`), carried through `FactRowData`/`LiveFactDetailData` (`use-facts.ts:63,145,334`). But the **review queue** — the screen the finding centred on ("the screen whose whole purpose is judging support") — still drops it: `use-review-queue.ts:123-141` (`factFromApi`) never copies `label_suppressed`, and `review-queue.tsx:161-165` renders rung + `UnderSourcedBadge` only. Chat context panel likewise. See new finding D-1. |
| **I-2** — CLAUDE.md "both arms dead-end on the unqualified judge" | **ADDRESSED** | Replaced by the re-derivation paragraph ("The audit's arms were re-derived…"), verified accurate against `contradiction_veto.py` and `_FALSE_PROMOTION_AUDIT_SQL`'s two arms. |
| **I-3** — "machine disputes unreachable until a qualification record exists" | **ADDRESSED** | CLAUDE.md now states the deterministic veto is judge-free and corpus-gated; ledger carries the Tier-3 second correction (`gate-ledger.md:620-635`). |
| **M-1** — bench guard `?database=` bypass | **ADDRESSED** | Folded into the F3 fix below. |
| **M-2** — F3 order-inertness guard cannot fail | **ADDRESSED** | Re-derived by mutation (drill A below). |

### Invariant-integrity review

| Finding | Verdict | Evidence |
|---|---|---|
| **F1** — "sole writer of `verified` events" false | **ADDRESSED** | CLAUDE.md's "One journaller for the machine's rungs" paragraph now names `ratify` as the second deliberate writer and why it cannot route through the first. |
| **F2** — stale `prune_orphan_entities` docstring | **ADDRESSED** | `graph.py:791-793` corrected with the dated note. |
| **F3** — repo-asserted merge oscillation | **Stands as recorded** (its own disposition was "recorded, not actioned"). |
| **F4** — supersession predicate "lives in both files" | **ADDRESSED** | CLAUDE.md now names `supersession.is_supersession_trigger` with the dated correction. |

### Silent-success review

| Finding | Verdict | Evidence |
|---|---|---|
| **F1** — order-inertness blind spot suite-wide | **ADDRESSED, re-derived** | Drill A: mutating `layer_composition.py:1006` to `(r.band, -r.tier, -r.weighted_score, r.key)` now reddens exactly `test_score_authority_cannot_re_enter_an_equal_tier_cross_channel_cell` (`test_layer_composition.py:1031`). The fixture's premises (one `(band, tier)` cell, fact carries larger magnitude) are asserted, not assumed. |
| **F2** — gate's measured-quantity arms cannot go red | **ADDRESSED** | F1 arm: `run_bench.py:313-359` `_assert_floors` raises `SystemExit` on any of four cells below the floors — and `GOLD_F1_FLOORS` (0.881/0.910/0.784/0.811) match the ledger's recorded G-B floors at `gate-ledger.md:347` exactly; no new tolerance was invented. The gate arm runs the default `gold.json`, so the floors are keyed to the corpus they were recorded on. Retrieval arm: renamed "retrieval eval replay" (`gate.sh:220-229`) with the reasoned refusal to add a post-hoc bar — the review's sanctioned option (b), and the reasoning ("a bar set after measuring") is itself the ledger's own rule. |
| **F3** — forbidden-database holes | **ADDRESSED** | New `benchlib/db_target.py` is the one rule (query-param override + percent-decode, `db_target.py:21-40`); adopted at `reset_bench_db` (`bench_db.py:104`), `BenchDatabase.__init__` (`:132`), `run_promotion_metrics.py:99`, `harvest_l2_facts.py:117`, `run_gc_evidence.py:133` — all five doors plus both destructive entry points. `test_db_target.py` pins the override case in one assertion; 28 tests re-run green. Closes recorded minor `:3023`. |
| **F4** — journal loss starves G-C's substrate | **ADDRESSED for the named callers** (T2.113, verified below) — with residue: new finding D-3. |
| **F5** — roster guard's stale "fourteen" | **ADDRESSED** (`test_code_deriver.py:1445`). |
| **F6** — T0.19 | Stands as recorded. |
| `:3010(d)` plan §2.3 | **ADDRESSED** — `968bd4f1` amends the plan with the shipped flagless signature; the reviewer's stated fallback side, correctly chosen (no T2.58 brief exists). |
| `:3010(e)` limit test pins length not head | **ADDRESSED, re-derived** — Drill B: `ordered[-limit:]` reddens exactly `test_the_cut_keeps_the_head_of_the_composed_order`; the length-only sibling stays green (65 passed / 1 failed). |
| `:3010(g)` comparator position untested | **ADDRESSED, re-derived** — Drill C: hoisting the `_UNCHANGED` lookup above the three older checks in `dream_undo.blocking_reason` reddens exactly the new precedence test; all 88 older tests stay green, matching the commit's claim. |
| Deferred-minor bookkeeping | The closure row (`E2-truth-core.md`, 2026-08-09) correctly says which entries remain live — (b), (c), (f) — and why. |

---

## Part 2 — the five unreviewed tasks, attacked

### T2.109 — veto rewire and the two bars

**The inertness claim holds structurally.** `decide` reads `contradiction_suspected`
exactly once (`verification_ladder.py:525`, into the recorded flag with the documented
confirmed-suppression), every return path flows through `settled()` which carries it
(`:546`), and no outcome depends on it — verified by reading every branch of the function.
`apply_demotion_hysteresis` preserves the flag through `replace()` (pinned at
`test_review_state_transitions.py:576-597`). `CONTRADICTION_DETECTORS` is one member
(`contradiction_veto.py:492-494`); `detect_scanned_contradiction`'s only caller under
`backend/app` is `recompute_fact`. The two parameters are genuinely separate.

**But the guard that pins inertness cannot fail on the mutation it most needs to catch**
— new finding D-2, demonstrated by mutation (drill D).

**The bars.** Git order confirms what the ledger discloses: `bb522848` (bars) landed after
`e7a10e2f`/`f3d8ac34` (the measured runs). The **recall bar is a genuine derivation with a
real falsifier**: doc 17 §6's pre-existing rule (truth-critical = 0.95) predates every run,
the measured judge does not clear it (0.945 < 0.95), and
`test_contradiction_recall_is_gated_and_barred_by_derivation`
(`test_verification_judge.py:135-149`) pins the value and pins it *against* 0.90. The
**precision bar 0.70 is not a derivation in the same sense**: §6's own rule would give the
non-critical metric 0.90; 0.70 comes from a review-load argument ("noise under one flag in
three") written into the amendment after three precision numbers (0.79/0.88/0.90) were
public — and 0.70 clears all three where 0.90 would have failed two. This is **not
laundering**, because every document carrying it says exactly this ("the controller had
already seen both judges' results… a reader who wants to discount them knows exactly what
to discount"), the gate's verdict does not ride on it (it fails on recall), and holding
precision at truth-pricing after the consumer changed would be its own dishonesty. But
CLAUDE.md's compressed "both by derivation from doc 17 §6's own rule" leans on the amended
§6; the recall half is the only one with a falsifier. Recorded, not actioned.

**The scorer incoherence is fixed for real**: `BAR_METRICS` carries the recall key
(`verification_judge.py:222-227`), `get_verification_bars` raises on an unstated bar
(`:374-379`), and the near-mute-judge gradient is closed by construction.

### T2.110 — gold growth

Numbers re-derived from the artifacts, not the prose: 351 = 241 + 110; contradicted 80
(declared = actual), which puts 76/80 = 0.9500 exactly on the lattice —
`test_the_contradicted_census_keeps_the_recall_bar_on_the_lattice` pins census % 20 == 0
and derives the modulus from the bar. Never-contacted subset: 110 pairs, 25 contradicted
(the 0.96/0.92 lattice finding in the ledger is arithmetically right). New pairs are
**proportional** to the old slice distribution (value-swap 13/110 ≈ 11.8% vs 29/241 ≈
12.0%) — no census-targeting visible, consistent with the blindness constraint. The
eg-0308 ruling is rule-then-pairs done properly: the exhaustivity rule is stated as a rule,
confirmed by two pre-existing unanimous adjudications (eg-0006, eg-0196), and the slice
re-adjudication changed no label. The ruling moved the gold's sha and the draw, manifest
and sheet were regenerated against it *before* the sitting (`49d1a27a` → `83dd57a9`), so
the certification sequence is clean. The resample (n=93 = 80-census + 13 proportional,
`bar_max_disagreements: 1` committed in the manifest before the sitting) passed at exactly
the bar, and LABELLING.md records that honestly ("the weakest passing sitting the set has
had"), classifies the one disagreement (eg-0018) against the window rule's own text, keeps
the standing LLM-sitting objection in force, and fixed a real artifact-collision bug it
found. This task survives attack. Residues: findings D-7 and D-8 (both structural, neither
verdict-changing).

### T2.111 — G-C re-measure

The numbers are unchanged and verified against the committed report
(`docs/eval/2026-08-08-promotion-metrics.md`: production `darkmem` 0 events; every probe
UNDER-POWERED). The re-derivation of the audit arms is accurate against shipped code
(`disputed_after`'s only producer is the deterministic detector; the scan reaches the audit
only via `rejected_after`), and the honest-cost paragraph (audit power strictly lower) is
the right direction of candour. The **third vacuity clause is the section's best work** —
it found the substrate hole, ruled it the one operable clause, and named the remedy — and
T2.113 closed it the next day. Residues: the ledger never says so (D-5), and the clause's
reach was one stream short (D-3).

### T2.112 — suspicion surfaced to the reviewer

**Backend: sound.** Columns in model + regenerated baseline
(`models/graph.py:115-116`, `0001_baseline.py:522-538`); marker written through the same
UPDATE statement as `verification_status` (`knowledge_triples.py:999-1011`, single
`assignments` list); `since` preserved across re-derivations
(`verification_ladder.py:970-988` `_suspicion_marker`, `opened_at` from the locked row);
self-clearing is real — `detect_scanned_contradiction` re-applies every guard at read time,
and the "later clean verdict" ground is genuine because the scan journals every completed
check with `"contradicted": finding is not None` (`contradiction_scan.py:609-610`);
dismissal ordering on the same `(created_at, id)` tuple as the recency rule
(`contradiction_veto.py:333-345,428-436`); replay override leaves the marker untouched
(`UNSET_SUSPICION`, `verification_ladder.py:1169-1179`); the dismiss door moves no
verification column and 409s on a lapsed flag (`review_queue.py:104-139` route,
`human_adjudication.py:300-374`); reason derivation reads the fact's own columns
(`review_queue.py:244-245`); counterpart served with expired counterparts deliberately
included (`_counterpart_triples`). 383 backend tests re-run green.

**Frontend: the task's title claim is false at the screen** — finding D-1, the delta's one
must-fix.

### T2.113 — journal atomicity

**Verified on both paths, and the pinning test is real.** `record_event` returns whether
the row landed (`events.py:158-222`), never raises, and its own SAVEPOINT leaves the
caller's transaction usable — so the raise in `set_verification_status`
(`knowledge_triples.py:1062-1081`) and `ratify` (`:1188-1198`) unwinds cleanly. The
callers that matter roll back: both `verification_recompute` arms wrap `recompute_fact` in
`session.begin_nested()` (`verification_recompute.py:512-523, 632-643`), so
`JournalWriteFailed` rolls the per-fact savepoint back including the UPDATE — the poisoned
fact settles alone and the atomicity claim holds on the production path, not just the HTTP
one. The pin test drops the current month's `events_YYYYMM` child table and drives a real
promotion into the real degradation path (`test_ladder_journaling.py:823-905`) — a
partition failure, not a mock — plus both halves of the return contract. Re-run green.
Residue: the fix stopped one stream short — finding D-3.

---

## Part 3 — new findings in the delta

**No Critical findings.** Four Important, five Minor.

### D-1 (Important, fix before merge) — T2.112's "surfaced to the reviewer" is wire-deep: the counterpart dies at the screen and the dismissal door has no caller

- `frontend/src/hooks/api/use-review-queue-api.ts:112,118-128` declares
  `suspected_contradiction` / `SuspectedContradiction` — and that is the **only** frontend
  reference to the suspicion (`rg suspect frontend/src` finds nothing else).
- `frontend/src/features/knowledge/use-review-queue.ts:123-141` (`factFromApi`) drops the
  field (and `label_suppressed` with it); `ReviewFactRowData` has no slot for either.
- `frontend/src/features/knowledge/components/review-queue.tsx` renders only
  `queued: <reason>`; no counterpart triple, no `suspected_at`, no expired-counterpart
  warning — the exact data `_counterpart_triples` exists to serve.
- `POST /review-queue/facts/{id}/dismiss-suspicion` has **zero** frontend callers (`rg -i
  dismiss frontend/src` finds only topics and settings); the reviewer who thinks the flag
  is wrong has no lawful action — the only button is Reject, which *confirms*.

**The failure it produces.** T2.112's done-when #2 — "the counterpart fact is reachable
from the queue entry, so the reviewer can compare" — is unmet at the only human surface;
the commit's own argument ("that only holds if a human can actually confirm it") fails at
its last hop. The ledger recorded this exact edge as load-bearing
(`gate-ledger.md:534-542`: the human route to the audit is "impassable… no reviewer can
confirm what they cannot see") — the delta opened it on the wire and left it shut at the
screen. CLAUDE.md's "gated on G-D passing *and* on the reviewer surface T2.112 shipped"
overstates what shipped. This is the third instance of the epic's
declared-on-the-wire/dead-at-the-screen shape, in the same delta that fixed the second
(I-1), and partially re-creates it (the review queue still shows neither marker). Nothing
live is affected today — the scan produces nothing behind the unqualified judge — but
merge makes "T2.112 done" baseline. **Fix is the same size as the I-1 fix**: carry
`suspected_contradiction` + `label_suppressed` through `factFromApi`, render the
counterpart line and `SuppressedBadge` on the queue row, add a dismiss button on the
`contradiction-suspected` reason; or honestly reopen T2.112.

### D-2 (Important, fix in the wave) — the inertness guard cannot fail on the highest-value mutation

`test_the_flag_changes_no_outcome_in_decide` (`test_review_state_transitions.py:548-561`)
claims to kill "a model verdict reaching a branch" but sweeps only
`OriginProfile(origins=())` — k=0, every fact below its bar. **Demonstrated by mutation
(drill D):** inserting

```python
if suspected and k >= n:
    return settled-like dispute (target "disputed", contradiction_blocked=True)
```

after `verification_ladder.py:525` — the model scan disputing every suspected fact that
meets its origin bar, precisely the rewire-reversal the split exists to forbid — passes
**410 tests across eight suites green** (`test_review_state_transitions`,
`test_contradiction_scan`, `test_contradiction_veto`, `test_ladder_journaling`,
`test_review_queue`, `test_demotion_hysteresis`, `test_deriver_lift`,
`test_verification_recompute`). The shipped code is correct (verified by read); the guard
is what cannot go red — the epic's recorded defect shape, on the redesign's central safety
property, in the test whose docstring claims mutation coverage. Fix: sweep profiles in the
loop (at-bar diverse origins, `supersession_blocked`, disputed-with-clean-verdict), not
just statuses.

### D-3 (Important, non-blocking; record on T2.40's re-measure) — T2.113 stopped one stream short: the audit's `rejected_after` arm can still silently lose its only substrate row

- `human_adjudication.record_human_verdict` (`human_adjudication.py:166-174`) ignores
  `record_event`'s return. A rejection's belief withdrawal (`expire`, `:198`) commits while
  the `human_verdict` row — the **only** journal record of a rejection, and the row
  `rejected_after` counts — silently fails. The audit then *undercounts false promotions*:
  the one direction that makes the gate read better than reality, exactly the failure class
  T2.113 was minted for. T2.109/T2.111 raised this row's load: `rejected_after` is now the
  LLM scan's only route into the audit.
- `dismiss_contradiction_suspicion` (`human_adjudication.py:352-366`) likewise ignores the
  return while its own docstring names the journalled event as "the durable reason it stays
  gone". On a journal failure the door answers 204, the marker clears, and the next
  recompute re-flags — the T2.62 bare-clear failure the commit says it avoids — and "the
  only live-data evidence of an LLM-scan false positive this system can produce" is lost.
- Consequently CLAUDE.md's new sentence "The **two** callers for whom the journal is
  load-bearing (`set_verification_status`, `ratify`)" undercounts; shipped code holds at
  least two more whose rows are load-bearing by the corpus's own arguments.

Fix is two return-checks and one CLAUDE.md word; the callers' transactions already own
both writes, so the raise composes the same way T2.113's does.

### D-4 (Important, doc fix in the wave) — `review_queue.py`'s module docstring is false against its own file

`app/services/review_queue.py:44-57` still asserts the suspicion "is persisted nowhere",
that a flagged fact "arrives here wearing `unspecified`", that closing the gap "is a design
call this module does not own" — while `:181-188` reads the two suspicion columns, `:244-245`
names `contradiction-suspected`, and `_suspicion_block` serves the counterpart. Line `:38`
("reads two columns and names two of the four reasons") is also stale (four and three).
T2.112 closed the gap and updated the count sentence's frame but left the T2.109-era
paragraph standing. Failure: the next task re-mints a closed gap or adds a second
persistence path — the invariant-23 shape, in a file whose *other* docstring paragraph
(`:77-83`) exists to correct a previous instance of exactly this.

### D-5 (Minor) — the gate ledger's two now-stale rulings carry no closing addendum

- Clause 3 of the G-C re-measure (`gate-ledger.md:567-578`) still ends "**it has no
  owner**" — T2.113 was minted from it (M1-measurement.md:262-305) and closed it on
  2026-08-09; the string "T2.113" appears nowhere in the ledger.
- The T2.112 cross-edge paragraph (`:534-542`) still says the human route is "impassable".

Both are dated records, but the ledger is the file gate claims are planned against, and
T2.40's re-measure will be planned by someone reading these sections. One dated addendum
line each.

### D-6 (Minor) — the re-measure's Rule-B subset table traces to no committed artifact

The ledger presents four never-contacted cells (`gate-ledger.md:709-714`: 1.0000 / 0.9778 /
0.9200 / 0.9200) and "Rule B was enforced for the first time here". The committed report
(`docs/eval/2026-08-08-judge-qualification-fd39e7b2.md`) contains no subset section — the
subset code landed in `47e3dce1`, the same commit that recorded the run, and the run's
recorded sha (`e69895cb`) predates it; the entailment cache the numbers derive from is
untracked (0 files in git). Checks that pass: the four cells are arithmetically consistent
with the report's pooled confusion (subset misses 2/25 contradicted, 1/45 entailed, FPs
2 — all folding correctly into the pooled 73/7, 145/1, 73+8 cells); the committed run
ledger holds exactly **one** attempt row for gold sha `800d4d91`, so "no extra gold
contact" survives its own counting rule (warm replays count). Verdict-neutral (the gate
fails on pooled recall regardless). Forward-closed: the runner now renders the subset
(`run_judge_qualification.py:264-269,295,330-341`). Record that this run's subset numbers
are ledger-only.

### D-7 (Minor) — the eligibility lock's resample certification is self-asserted

`judge_qualification.gate_eligibility` (`judge_qualification.py:173-227`) validates only
that gold.json's embedded `resample` block says n ≥ 93, disagreements ≤ 1, and carries
citation fields. Nothing binds the certification to the pair content it certified: a
post-certification label flip keeps eligibility green on a certification of a different
file. The growth round handled this correctly by *procedure* (the carried-over block was
stripped, LABELLING.md:634-642, precisely because "keeping it would have satisfied the
eligibility lock with a certification of a different file") — the code does not enforce
what the protocol already understands. The slice-count pin test catches appends but not
label flips. Fix shape: record a pairs-only content hash in the resample block and
re-derive it at eligibility time.

### D-8 (Minor) — certified sha ≠ measured sha, and annotation resets the attempt counter

The sitting wrote its certification *into* gold.json (`83dd57a9`), moving the sha: the
manifest and raw-reply artifact certify `047cbd6f…`, the gate run measured `800d4d91…`.
Verified metadata-only (the 83dd57a9 gold diff is exactly the `resample` block), so the
pairs certified are the pairs measured — but the discontinuity is invisible to a reader
comparing the two artifacts, and `gold_touching_attempts` (keyed on file sha) resets on any
annotation, so the two-attempt budget is trackable only across shas by hand. Interacts
with D-7; same fix (content-hash the pairs, key both the certification and the attempt
counter on it).

### D-9 (Minor) — stale reason enumeration on the queue row type

`frontend/src/features/knowledge/use-review-queue.ts:52-55`: `reason`'s docstring
enumerates `'disputed' | 'under-sourced' | 'unspecified'`; the backend now also serves
`contradiction-suspected`. Carried verbatim so nothing breaks; the enumeration is now the
lie. One-line fix, rides D-1.

---

## Checks re-run vs inherited

**Re-run on this checkout:** four mutation drills (A: `-weighted_score` tie-break; B:
`[-limit:]` cut; C: hoisted comparator; D: flag-disputes-at-bar), each snapshot/restore
with `git status` clean after; scoped suites totalling ~1,050 tests green on clean source
(`test_layer_composition` 66, `test_dream_undo` 89, `test_review_state_transitions` +
`test_ladder_journaling` batch 211, `test_review_queue`/`test_contradiction_scan`/
`test_contradiction_veto`/`test_verification_judge`/`test_demotion_hysteresis`/
`test_deriver_lift` 383+17s, drill-D wide net 151, benchlib `test_db_target` +
`test_gate_bench_db_env` 28, frontend `articles-tab.real` + `suppression-visible` 6);
gold census arithmetic recomputed from `gold.json` (351/80/110/25, slice proportionality);
`GOLD_F1_FLOORS` diffed against ledger `:347`; run-ledger attempt rows counted for sha
`800d4d91` (exactly 1); every `file:line` cited above read in the working tree.

**Inherited:** the three judge-qualification runs' measured cells (API cost; pooled cells
cross-checked against the committed report's confusion table); the resample sitting's raw
replies (committed, not re-scored); the never-contacted subset cells (no committed basis —
D-6); the G-D resolution spike's cache-replay attributions; the frontend C-1 commit's own
mutation claim (structure verified by read); G-B baseline cells. The merge gate was not
run (a full run was already in flight in this tree, and it moved HEAD mid-review —
`3f5da2ad`, verified docs-only).

---

## Merge verdict for this delta

**Blocks merge: D-1.** T2.112 is claimed done and baseline-worthy while its done-when #2
is unmet at the only human surface and its dismissal door is unreachable by the reviewer
it exists for — under this lens, a task-completion claim whose evidence does not exist.
The fix is small and has same-delta precedent (the I-1 fix); alternatively, honestly
reopen T2.112 and amend CLAUDE.md's "reviewer surface T2.112 shipped" sentence. Completing
D-1 should also finish I-1's remaining half (the queue and chat panel still drop
`label_suppressed`).

**Fix in the same wave, cheap, non-blocking:** D-2 (one profile sweep in an existing
test), D-3 (two return-checks + one CLAUDE.md word), D-4 (docstring), D-9 (rides D-1).

**Record, may stand:** D-5 (two ledger addenda), D-6 (subset provenance note), D-7/D-8
(content-hash the certification — a real hardening, correctly not urgent while the
protocol's own discipline holds).

**Everything else in the delta withstood attack.** The fix wave's mutation-evidence claims
were all re-derivable; both gate-arm changes make the instrument stricter without inventing
numbers; T2.110's gold discipline is the best-executed measurement work on the branch;
T2.111's re-derivation is accurate against shipped code and states its own costs; T2.113
is correct on both paths with a genuinely un-mocked failure drill. G-C and G-D remain NOT
CLEARED, on purpose, and every claim about those numbers that I could test held.
