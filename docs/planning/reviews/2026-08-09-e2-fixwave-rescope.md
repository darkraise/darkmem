# E2 fix-wave scoped re-review (2026-08-09)

**Scope:** the six-commit fix round `149f1f1e..97f9c8f3` against the open findings of
`2026-08-09-e2-delta-review.md` (D-1…D-6, D-9) plus I-1's remaining half from
`2026-08-08-e2-branch-review-claim-honesty.md`. **Method:** every verdict below is
re-derived on this checkout, not read off the fix report — the diff file was byte-compared
against the actual commit range (`diff` clean), the reviewed files were confirmed identical
between `master` and the working branch (`git diff --stat master HEAD` empty for all of
them), and six mutation drills were run (snapshot → mutate → scoped pytest/vitest →
restore → tracked-file status clean after each). Backend runs hit real Postgres on
`darkmem_test`; two runs collided with concurrent sessions' pytest processes (schema-setup
race on `alembic_version`) and were re-run clean — every count cited below is from an
uncontended run.

**Verdict up front: five of eight fully addressed, one addressed with two doc-only
residues, two remain partially open.** D-1 — the round's blocker — is genuinely closed and
its three new tests all redden under mutation. D-2 is the miss that matters: the
strengthened sweep kills the named reversal but still cannot fail on the third profile
shape the finding's own fix line prescribed (`disputed-with-clean-verdict`) — demonstrated
by a mutation that passes 411 tests across all eight suites. I-1's chat-panel half was not
attempted. No Critical or Important new breakage was introduced by the fixes.

---

## Per-finding verdicts

| Finding | Verdict | Settled by |
|---|---|---|
| **D-1** (blocking) — suspicion wire-deep, dismissal door uncalled | **ADDRESSED** | `use-review-queue.ts:145-146` carries both fields; `review-queue.tsx:221` (SuspicionBlock), `:204-206` (SuppressedBadge), `:240-249` (dismiss button), dialog → `useDismissSuspicion` (`use-review-queue-api.ts:203-225`); 3 new tests, all mutation-verified |
| **D-2** — inertness guard cannot fail on the reversal | **PARTIALLY ADDRESSED** | Named mutation now reddens (`test_review_state_transitions.py:596`); recovery-door reversal still passes 411/411 — see drill R2 |
| **D-3** — verdict/dismissal journal loss | **ADDRESSED** | `human_adjudication.py:184`, `:391`; both guards mutation-verified; ordering and unwind verified at the call sites |
| **D-4** — `review_queue.py` docstring false | **ADDRESSED** (2 doc residues) | Module docstring `:38`, `:42-62` corrected and verified claim-by-claim; residues below |
| **D-5** — two stale ledger rulings | **ADDRESSED** | `gate-ledger.md:544-553`, `:591-601`; every commit hash named checks out |
| **D-6** — subset table provenance | **ADDRESSED** | `gate-ledger.md:739-750` provenance note; runner renders subset (`run_judge_qualification.py:268,295,331`) |
| **D-9** — stale reason enumeration | **ADDRESSED** | `use-review-queue.ts:52-55` now enumerates `contradiction-suspected` |
| **I-1** (carried) — suppression dies at the screen | **PARTIALLY ADDRESSED** | Queue half closed (mutation-verified); chat context panel untouched — see below |

---

## D-1 — verified at every layer

- **Wire:** backend serves both fields on every queue item — `_served_labels` spread at
  `review_queue.py:456` (`label_suppressed`), `_suspicion_block` at `:471`. Field names in
  `_suspicion_block` (`review_queue.py:292-298`) match the frontend
  `SuspectedContradiction` interface (`use-review-queue-api.ts:118-128`) **field for
  field** — checked deliberately, because the vitest suite mocks `apiFetch` and would pass
  on a name mismatch that dies live.
- **Screen, default detail level:** the detail-level store defaults to `"advanced"`
  (`use-detail-level.ts:14`); `SuspicionBlock`, `SuppressedBadge` and the dismiss button
  are **level-unconditional** in `FactRow` (only `ConsequenceBreakdown`/`EvidenceBlock`
  are gated, `review-queue.tsx:229-230`), and the new tests pin the *stricter* `"simple"`
  level, so both levels are covered.
- **Mutations (each restored, tree clean after):**
  - remove `<SuspicionBlock fact={fact} />` → exactly `renders the counterpart and the
    suppressed label` fails (26/27);
  - remove the `SuppressedBadge` conditional → same test fails on `label withheld`;
  - neuter `runDismiss`'s `mutate` call → exactly `offers a dismissal, and it posts to the
    dismissal door` fails.
- **Action correctness:** confirm-before-post asserted (no call from the button alone),
  posts to `/review-queue/facts/{id}/dismiss-suspicion` and provably not to `/reject`;
  demo path cannot reach the button (`factFromDemo` pins both fields null,
  `use-review-queue.ts:193-198`). `npm run typecheck` green.

## D-2 — the named reversal dies; a named sibling still cannot

**Drill R1 (the finding's named mutation), reddens.** Inserting
`if suspected and k >= n: return settled("disputed", "dispute", blocked=True)` after the
`settled` closure in `decide` fails exactly
`TestTheSuspectedContradictionOpener::test_the_flag_changes_no_outcome_in_decide`
(`test_review_state_transitions.py:596`, 1 failed / 3 passed in the class). The premise
assertion (`:601-603` — at-bar candidate actually promotes) blocks the sweep from quietly
regressing to all-holds. This half of the fix is real.

**Drill R2 (the finding's third named shape), does not redden anywhere.** D-2's fix line
prescribed sweeping "at-bar diverse origins, `supersession_blocked`,
**disputed-with-clean-verdict**". The shipped sweep (`:583-596`) varies profiles × blocked
× statuses but never `open_contradiction` — every `decide` call takes the `NO_DETECTOR`
default, under which the disputed branch holds unconditionally. Inserting

```python
if suspected and open_contradiction is False:
    return settled("disputed", "hold")
```

at the top of the disputed branch — the model scan blocking recovery out of `disputed` on
an affirmative clean verdict, i.e. the scan sustaining a dispute, a real flag-conditioned
rung outcome reachable in production (`recompute_fact` passes both parameters
independently) — ran **411 passed, 17 skipped, 0 failed** across the same eight suites the
original drill-D used (`test_review_state_transitions`, `test_contradiction_scan`,
`test_contradiction_veto`, `test_ladder_journaling`, `test_review_queue`,
`test_demotion_hysteresis`, `test_deriver_lift`, `test_verification_recompute`). No test
in the tree passes `contradiction_suspected=True` outside
`test_review_state_transitions.py` (rg), so no other suite can catch it either.

The new test docstring is honest about what it covers ("the two blocked paths") — it makes
no false claim; the sweep simply does not discharge the finding's full prescription.
**Remains open, small:** add the `open_contradiction=False` cell for `current="disputed"`
(or sweep the verdict axis) to the same loop.

## D-3 — both guards real, both call sites unwind

- Exactly **four** `raise JournalWriteFailed` sites exist under `backend/app`
  (`knowledge_triples.py:1084,1202`; `human_adjudication.py:184,391`), matching CLAUDE.md's
  corrected count exactly; no `except JournalWriteFailed` exists anywhere in `app/`, so
  nothing swallows it.
- **Ordering.** `dismiss_contradiction_suspicion` journals (`:368`), raises on `False`
  (`:385-395`), and only then clears the marker (`:396-398`) — the clear is strictly after
  the journal, and the new backend test pins that order (it reads the still-set flag after
  the raise). `reject_fact` expires first (`:212`) then journals (`:213`), so the raise
  leaves the expire in the session — and both routes (`routes/review_queue.py:93-102`,
  `:129-139`) commit only after the door returns, while `get_session`
  (`app/database.py:28-35`) rolls back on any raise propagating through the yield, so the
  belief withdrawal unwinds. `record_event`'s own SAVEPOINT keeps the session usable
  through the failed insert, so the rollback is clean, not a poisoned-transaction abort.
- **Mutations:** disabling each guard (`if not journalled:` → `if False:`) fails exactly
  its test — `test_a_rejection_that_cannot_be_journalled_does_not_happen` and
  `test_a_dismissal_that_cannot_be_journalled_does_not_clear_the_flag` — both driven
  through a real dropped partition, not a mock. Clean baseline: 27/27 and the full
  `test_review_queue.py` green.
- `ratify_fact` also routes through `record_human_verdict` (`:303`), so the ratification
  verdict row gets the same contract for free — consistent, not accidental.

## D-4 — corrected where named; two residues in the same file

The rewritten module docstring's claims were verified individually: the module now reads
four columns (`_FACT_COLUMN_NAMES:182-192`) and names three of four reasons
(`_fact_reason:245-251`); the invariant-15 scan claim is **accurate as written** — the
veto-reference scan (`test_contradiction_veto.py:1311-1328`) is text-based over
non-comment lines, exempting only `#`-prefixed lines, so a *docstring* naming
`app.services.contradiction_veto` would fail the build (the `#` comment at
`review_queue.py:187` is exempt; the docstring paragraph deliberately never spells the
path). Residues:

1. **Fix-induced dangling citation (new breakage, Minor).** `_fact_reason`'s function
   docstring (`review_queue.py:230-236`) still says the contradiction-suspected fact "has
   no column at all" and falls through to `unspecified` — false against its own body three
   lines below (`:249-250`) — and cites "the module docstring says what closing that would
   cost", a paragraph **this fix deleted**. The "no column" clause predates the wave
   (stale since T2.112); the dangling citation is `1aff6d21`'s own.
2. **"The same scan" misattribution (Minor).** The new paragraph's closing sentence
   attributes the event-type-channel guard ("the three modules that declare, write and
   read it") to invariant 15's scan. They are two different tests with different
   mechanisms: the channel guard is the AST allowlist scan in
   `test_contradiction_scan.py` (G2b, `_VERDICT_REFERENCE_ALLOWLIST:748-752`); the
   veto-reference scan is `_forbidden_veto_references` in `test_contradiction_veto.py`.

## D-5 / D-6 — addenda accurate

Every commit hash named in both addenda checks out against `git log` and against the code
it describes (`0d9b5dca`, `149f1f1e`, `90b8fc7f`, `f0b2a2ed`); T2.113's minting clause
exists at `M1-measurement.md:262`. "Closed on both streams / trusted in both directions"
is supported by the four raise sites covering the `verified`, `human_verdict` and
`contradiction_dismissed` streams — the ones doc 17 §5.1's metrics and the dismissal
persistence read. The D-6 note records exactly the checks the delta review ran, claims no
more, and its forward-closure claim is verified (`run_judge_qualification.py:268,295,331`
render the never-contacted subset). The D-7/D-8 parking row exists in M1-measurement.md's
amendment log with the fix shape recorded.

## I-1 — one half of the remaining half

The review queue now carries and renders `label_suppressed` (mutation-verified above).
The **chat context panel does not**: `ChatContextFact`
(`frontend/src/features/chat/lib/retrieval.ts:62-74`) has no `label_suppressed` slot even
though the backend chat door serves the field (`app/services/chat.py:407`), and
`chat-context-panel.tsx` renders `VerificationBadge` + badge claim with no
`SuppressedBadge`. The panel is not *dishonest* — it shows the served (gated) rung, and
`fact_badge` withholds the badge sentence a withheld rung can't carry — but the reviewer
is not told a label was withheld, which is the exact I-1 complaint, on the surface the
delta review's merge verdict named. **Remains open**; the fix is the same one-field,
one-badge shape as the queue's.

---

## New breakage in the fix diff

**No Critical, no Important.** Checked: route/transaction composition of the two new
raises (unwinds, above); no exception swallower; frontend typecheck; wire field-name
parity between `_suspicion_block` and `SuspectedContradiction`; demo-mode reachability of
the dismiss button (unreachable, by fixture shape, consistent with the no-demo-arm
comment); query invalidation keys on dismissal. Two Minor doc items, both recorded under
D-4 above (the dangling `_fact_reason` citation is the only one the fix itself created).

## Out-of-scope observations (deferred minors — recorded, not looped on)

- `_fact_reason`'s "has no column at all" clause was already false before this wave
  (stale since T2.112 landed the column read); the delta review's D-4 named only the
  module docstring, so this sat one screen below its scope. Folded into the D-4 residue
  above; one docstring edit clears both clauses.
- Concurrent agent sessions run pytest against the shared `darkmem_test` database and the
  conftest's DROP SCHEMA/upgrade races produce spurious errors *and* spurious assertion
  failures in whichever session loses (observed twice in this review, including a
  22-failure phantom run that was 411-green when re-run uncontended). Any future
  mutation-drill claim made from a contended run is unreliable in both directions; worth a
  note in the runbook, not a code change.

---

## Overall verdict

**Not fully closed; the remainder is small.** Open after this round:

1. **D-2 residue (Important, one-loop fix):** extend the inertness sweep with the
   `disputed` × `open_contradiction=False` cell (with and without the flag) so the
   recovery-door reversal reddens — the third profile shape the finding prescribed and
   the one drill R2 proves is still invisible.
2. **I-1 residue (Minor-to-Important, one-loop fix):** carry `label_suppressed` onto
   `ChatContextFact` and render `SuppressedBadge` in the chat context panel.

Everything else — D-1 including its blocker status, D-3, D-4 (module docstring), D-5,
D-6, D-9 — is addressed with evidence that survived mutation. The two doc minors (D-4
residues) can ride whichever commit closes item 1.
