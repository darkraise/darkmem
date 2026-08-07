# E2 whole-branch review — claim honesty (2026-08-08)

**Lens:** does every claim this branch makes — code, config, docs, serving surfaces —
rest on evidence that actually exists? **Branch:** `feat/e2-truth-core` at `c510e8ae`.
**Method:** every finding below was verified against shipped code (file:line cited), not
task text or prior reviews. Where a check was inherited rather than re-run, that is said.

**Verdict up front: NOT merge-ready under this lens.** One Critical (a real-mode UI
surface serving fabricated `corroborated`/`confirmed` articles), three Important, two
minors worth the fix wave. The backend perimeter itself held everywhere I probed it —
the Critical is a frontend surface the backend gates never see.

---

## Findings

### C-1 (Critical) — Real mode serves fabricated L3 articles carrying `corroborated`/`confirmed` badges, claim strings, and coverage numbers

Verified against code:

- `frontend/src/features/knowledge/components/articles-tab.tsx:71` —
  `const articles = useDemoArticles()` **unconditionally**. Every sibling surface
  branches on `DEMO` (`fact-detail.tsx:39`, `use-facts.ts`, `review-queue.tsx:285`,
  `hygiene-queue.tsx:481`); this one never does.
- `frontend/src/routes/_authenticated/knowledge_.articles_.$articleId.tsx:132–133` —
  the detail page likewise renders `useDemoArticle` / `useDemoFacts` unconditionally.
- `frontend/src/demo/store.ts:66` — `CURATED_ARTICLES` are seeded into the store at
  creation, regardless of mode.
- `frontend/src/routes/_authenticated.tsx:58` — "Articles" is an **unconditional**
  first-class nav destination in the authenticated app.
- `frontend/src/demo/data/knowledge-curated.ts:44,50,111,…` — the curated articles are
  in project **`darkmem`** (the owner's real project) with
  `verification_status: "confirmed"` / `"corroborated"`, claim sentences, and
  "claim-support coverage 0.92"-style ratios.
- `frontend/src/routes/_authenticated/knowledge_.articles.tsx` — page chrome asserts
  "L3 synthesised articles — grounded prose whose every claim links to a verified fact."

**The failure it produces.** An authenticated reader of a *real* deployment (prod
compose serves this SPA) opens Knowledge → Articles from the sidebar and is served
eight invented articles asserting verification the system never performed — while on
the backend the article channel does not exist (T3.02), `groundedness_gate()` is
closed **unconditionally**, a scan pins that nothing under `app/` emits a `grounded`
literal, and G-C/G-D are both open. Every guarantee T2.95/T2.99/T2.100 built is
bypassed by a screen rendered from fixture data. The coverage ratio is a number G-E
owns and has never measured. Worse, the honesty e2e
(`frontend/tests/honesty/labels-always-render.spec.ts`) drives the article detail "in
both modes" and asserts the badge *renders* — institutionalising the fabricated badge
as a tested property.

**Corpus state.** T2.86's amendment row (`E2-truth-core.md`, 2026-08-04) noticed the
*detail* route "has the same shape" and declined to mint, arguing there is "nothing
live to wire it to." That reasoning answers the wiring question and never confronts
the serving question — and the *list* tab and the *nav entry* were never examined at
all. This is not one of the three settled rulings; it is a new finding.

**Blocks merge.** The cheap fix follows T2.86's own precedent (close by not offering):
gate both article surfaces on `DEMO` — the honest real-mode rendering already exists
in the tab's own `EmptyState` copy — and hide or demo-tag the nav entry in real mode.

### I-2 (Important) — CLAUDE.md still asserts the claim ruling 2 corrected: "both its arms (machine dispute, human rejection) dead-end on the unqualified judge"

- `CLAUDE.md:724–727` (current, on disk): "the false-promotion audit cannot produce a
  non-vacuous number before the judge qualifies — both its arms (machine dispute,
  human rejection) dead-end on the unqualified judge."
- Ruling 2 (`c510e8ae`, ratified) corrected exactly this in the ledger
  (`gate-ledger.md:536–550`): `human_adjudication.reject_fact` accepts any fact id
  with **no judge on its path** and journals the `human_verdict` event the audit's
  `rejected_after` CTE counts. Verified in shipped code
  (`app/services/human_adjudication.py:177–218`) and stated independently by the
  artifact itself (`docs/eval/2026-08-07-promotion-metrics.md`: "The human-rejected
  half is live as of T2.63").
- `c510e8ae` touched doc 20, the ledger, M1 and the analysis — **not CLAUDE.md**.

**Failure produced:** the contract file misinforms every future task about a live
audit arm — precisely the misplanning the ruling's own commit message says it exists
to prevent. Ruling 2 was applied correctly but **incompletely**. Fix before merge
(one-paragraph edit; contrast ruling 1 at `9e9b0367`, which edited CLAUDE.md in the
same commit and is applied completely).

### I-3 (Important) — "Machine disputes are unreachable until a qualification record exists" is false: the deterministic veto arm is live and judge-free

- `CLAUDE.md:694–697`: the veto's "only instrument is the qualified `verification`
  judge, so **machine disputes are unreachable until a qualification record exists**."
- The ledger's G-C verdict item 2 carries the same overstatement: "Machine disputes
  flow only through `contradiction_scan` → `VerificationJudge.judge()`."
- Shipped code: `app/services/contradiction_veto.py:228` —
  `detect_open_contradiction`'s **inverse-replacement arm is live** (fires on
  REPLACES-family edges asserted in both directions, overlapping windows, non-echo
  attributable witness; `SINGLE_VALUED_RELATIONS` being empty narrows, does not
  disable it). It is adjudicated on **every** recompute at
  `app/services/verification_ladder.py:999–1013` (`adjudicate_contradiction_finding`)
  with no judge, no qualification record, and no config anywhere on the path, and its
  dispute journals a `verified` transition the false-promotion audit would count. The
  module's own docstring says the deterministic half is "adjudicated here in full";
  only the Tier-C **LLM** scan aborts on the unqualified judge.
- The corpus itself concedes this obliquely: ruling 3's clause
  (`M1-measurement.md:329`) needs "no REPLACES-family edge in the corpus" for the
  audit numerator to be structurally zero — a condition that only matters because the
  deterministic arm can dispute.
- Not re-litigation: `analyses/2026-08-07-gate-ordering.md` never mentions the
  deterministic scan; ruling 2 narrowed the human arm only.

**Failure produced:** two contract documents overstate darkness in the *over-claiming*
direction for a limitation (the false claim here is "this cannot happen", about a
safety-relevant dispute mechanism). T2.40's re-measure would inherit a wrong premise:
a machine dispute in a future window would read as impossible. G-C's verdict itself is
unaffected (under-powered stands regardless). Fix before merge: correct the CLAUDE.md
sentence; the ledger sentence needs a Tier-3 amendment narrowing "machine disputes
flow only through the LLM scan" to the LLM arm.

### I-1 (Important) — The suppression marker dies at the screen: no frontend surface renders `label_suppressed`

- Declared on the wire types, with the reason spelled out:
  `frontend/src/hooks/api/use-knowledge-api.ts:53–55` ("Without it a suppressed row
  and a genuine candidate look alike"), `use-review-queue-api.ts:62,102`.
- Never carried further: `use-facts.ts`'s `FactRowData` has no such field, and
  `rg label_suppressed frontend/src` finds **zero** rendering sites — facts tab, fact
  detail, review queue, chat context panel all drop it.

**Failure produced.** The epic's second stated property — "suppression must be
visible … or a missing measurement silently becomes an apparent property of the
corpus" (`tests/test_claim_serving_gates.py` charter; `claim_gates.py` docstring) —
holds at the wire and fails at the human. A suppressed fact renders as a `candidate`
badge with no claim sentence and no origin count (the badge is nulled with the label,
`fact_badge.row_labels`), which reads as *missing data*, not as "the verifier is
unmeasured." An operator triaging the review queue — the screen whose whole purpose is
judging support — cannot tell a withheld `corroborated` from a genuine `candidate`.
The direction of error is under-claiming, so no unbacked claim is served; but the
distinguishability half of the branch's own contract is unimplemented at its only
human-facing surface. Fix in the consolidated wave (carry the field through
`FactRowData` and the review-queue/detail adapters, render the reason).

### M-1 (Minor, fix in the wave) — bench DB guard still bypassed by a query parameter

`backend/scripts/benchlib/run_promotion_metrics.py:88–110` — `_assert_not_forbidden`
reads only `make_url(url).database` (percent-decoded, per the T2.51 fix), so
`…/darkmem_bench?database=darkmem_test` still reaches the forbidden database exactly
as ledger row `E2-truth-core.md:3023` recorded. Verified current. The exposure is the
one the row names: a gate-evidence runner measuring a database mid-`DROP SCHEMA` and
emitting a garbage number into a gate report — small, deliberate-construction-only,
but it sits under gate evidence, and the fix is a few lines (refuse or fold in query
`database`/`dbname` params). Recommend taking it in the fix wave; may stand if declined.

### M-2 (Minor, mint a task) — the F3 order-inertness guard cannot fail on the mutation it most needs to catch

Ledger `:3010`(a), spot-checked still open: no equal-tier cross-channel fixture exists
in `backend/tests/test_queue_ranking.py`, so inserting `-weighted_score` as a
tie-break after band and tier passes all 46 tests. A green guard that cannot go red is
the epic's own recorded defect shape, and this ordering claim will be *trusted* by M1
triage. One fixture closes it. Not a merge blocker.

---

## What held (verified, not inherited)

- **The perimeter.** No promotion record exists on disk, in git history, or tracked
  (`git log --all -- '**/promotion_metrics_record.json'` empty); no
  `verification_qualification.json` either. Nothing in the tree mints the record —
  `run_gc_evidence.py` states and implements the refusal ("never as a side effect of
  measuring"); the only writer is a deliberate human act.
- **The gate.** `corroboration_gate` fails closed on absent/corrupt/interim/truthy-
  non-boolean records; `served_status` / `raw_statuses_for_served` /
  `gated_journal_payload` were re-driven: `tests/test_claim_serving_gates.py` +
  `test_fact_badge.py` = **154 passed** on this checkout, unfixtured door drives
  included (REST list/detail, MCP `fact_get`/`knowledge_search`, review queue, chat
  context, topics counts, filter inversion, ladder/evidence embeddings, whole-body
  string search).
- **API perimeter is closed.** Only `facts.py`, `review_queue.py`, and the knowledge
  schemas carry `verification_status` in the API layer; the websocket broadcasts are
  memory-side; MCP exposes only the two gated fact tools; `memory_overview` states it
  carries no badge; ratify/reject are REST-only 204s whose unserved returns were
  verified discarded.
- **Floors clamp.** `verification_ladder.get_ladder_config` clamps below-floor values
  first (ordering bug fixed and pinned), holds even *measured* origin counts at ≥ 1,
  and `ladder_measurements` has **zero writers** in the tree and no generic
  key-value REST door (`app/api/routes/config.py` is all typed endpoints). Note
  honestly: "by a recorded G-C measurement" is enforced as *procedure* (the row's only
  intended writer), not code — the code enforces per-parameter naming; the docstring
  says so plainly.
- **Veto absoluteness.** `decide` honours `open_contradiction` before every count with
  no config on the branch (`verification_ladder.py:522`); demotion hysteresis touches
  only the below-N `demote` outcome, never the dispute; D4's scan
  (`test_contradiction_veto.py:631`) fails the build on a config read in the detector.
- **Born rows.** `_write_born_rung` is the one statement writing the rung, refuses via
  `_MACHINE_WRITABLE_VERIFICATION_STATUSES`, and the exclusion is stated **where the
  number lives**: G-C bars R2/R3 (`gate-ledger.md:479–491`), the completeness probe's
  carve-out column, and verdict item 3 ("the badge outruns the measurement — say so
  here"). Nothing else counts them: the aggregate sweep pins `pin_suggestions`
  (gate-inverted) and `review_ranking` (whose only rung predicate is `disputed`,
  verified at `review_ranking.py:476–481`).
- **`confirmed` is human-only in SQL**: `ratify`'s human-source precondition rides the
  UPDATE's own WHERE; `set_verification_status` refuses the value.
- **Ledger numbers.** The G-C artifacts exist and agree with the ledger rows
  (production probe: 0 events; bench: 62 facts / 0 transitions / 0 carve-out). The F1
  cells were re-verified green by the review package 2026-08-07/08 (inherited). I did
  **not** re-run the bench G-C evidence end-to-end (LAN embedder dependency); its SQL
  and bars are committed and pin-tested.

---

## Ruling-application check (the three settled 2026-08-07/08)

| Ruling | Applied? | Note |
|---|---|---|
| 1 — doc 10 §6 scoping key (`9e9b0367`) | **Completely.** | Doc 10 §6 now scopes on `detail.file_path`; CLAUDE.md was updated in the same commit and now correctly records the shipped sha-comparison as the deliberate deviation; Option B correctly not adopted. |
| 2 — G-C→G-D cross-edge (`c510e8ae`) | **Correctly but incompletely.** | Ledger correction block present, doc 20 + M1 updated. CLAUDE.md missed → finding I-2. The corrected ledger sentence also still overstates the machine arm → finding I-3 (new, not re-litigation). |
| 3 — vacuity clause | **Completely.** | Recorded on T2.40 at `M1-measurement.md:329`, open by design, with the bar-attribution sharpening. Left alone as instructed. |

## Triage — deferred minors and parked items

| Item | Verdict | Reason (through this lens) |
|---|---|---|
| `:3006` — dead `cycle_id`; untested `created_at` floor; unpinned `_none` sentinel; undo read-path guard perimeter | **May stand** | None serves a claim; the tombstone sentinel is verified doubly inert in the row itself. Bundle with the next `dream_undo` touch. |
| `:3010`(a) — F3 order-inertness blind spot | **Mint a task** (not a blocker) | Verified still open (M-2). A guard that cannot fail, on an ordering claim M1 will trust. |
| `:3010`(b,c,e,f,g) | **May stand** | Unasserted paths and message wording; (c) is blocked on T3.02's producer anyway. |
| `:3010`(d) — plan §2.3 still names `with_trace` | **May stand; amendment owed** | T2.58 landed the flagless seam; a plan/code divergence with a named owner, no serving consequence. |
| `:3013`(1) — Phase W score-order mirror of I1 | **May stand** | Verified still open (`memory_dream.py:524` sorts by score). Same end-state across cycles; within-cycle transient only. Note it is now two tasks past its "T2.23's domain" tag with no owner — fold into the next dream touch or it will drift forever. |
| `:3013`(2–5) | **May stand** | Narrower than any realistic failure; observability-only. |
| `:3023` — `_assert_not_forbidden` query-param bypass | **Fix in the wave** (M-1) | Verified still open; sits under gate evidence; few-line fix. Not a blocker. |
| `:3025` — `add_source` spares uninterpretable refs | **May stand** | Documented at the minting site and executably pinned; a hardening opportunity, not an open defect. |
| T0.19 — relative `--git-common-dir` → empty `MAIN_CHECKOUT` | **Correctly left** | Verified: needs a main checkout with no `.venv` *and* a CWD outside any repo; the failure is loud (missing interpreter → `GATE BLOCKED`), never a silently green gate. |

---

## Merge verdict

**Blocks merge:** C-1. A branch whose thesis is "no reader receives a verification
claim whose evidence does not exist" cannot merge while its own navigation serves
fabricated `corroborated`/`confirmed` articles — in the owner's real project name,
with invented coverage numbers — to every real-mode reader. The fix is small and has
in-branch precedent (DEMO-gate both article surfaces to the existing honest empty
state; hide or demo-tag the nav entry).

**Fix before merge, cheap:** I-2 and I-3 (CLAUDE.md is the contract file and both
sentences misinform the next task; I-3 also needs a Tier-3 ledger amendment). I-1
(carry and render `label_suppressed`) — the suppression-visibility half of the
branch's own contract, currently true only for API readers.

**Does not block:** M-1/M-2 and every triaged deferred minor; the backend claim-gate
perimeter, the floors, the veto, the born-rung accounting, and the ledger's G-C
recording all withstood adversarial probing.
