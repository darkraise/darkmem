# E2 whole-branch review — lens: silent success (2026-08-08)

Adversarial pre-merge review of `feat/e2-truth-core` at `c510e8ae` against `master`
`19c6450c`, through the assigned lens: **checks, guards, scans, gates and tests that
pass without being able to fail, and behaviours that fail without producing a
symptom.** Every finding below is **verified against the shipped code** (file:line
cited); anything inferred is labelled as such. Mutation drills were run and reverted
by copying back a pre-mutation snapshot of the single mutated file; the tree was
verified clean (`git status` empty) after each drill.

Method note on one drill: the first full-suite run against the F1 mutation used
`-x` and stopped on a failure in `tests/test_communities.py`. That failure was
environmental, not a catch — the same file passes on clean source and passed inside
the complete mutated run recorded below. It is disclosed here rather than dropped.

---

## Findings

**No Critical findings under this lens.** Six findings: four Important, two Minor.

### F1 — Important — the F3 order-inertness blind spot is real and suite-wide, not 46-tests-wide

**Verified by mutation.** `backend/app/services/layer_composition.py:1006` is the
composed order:

```python
ordered = sorted(rows, key=lambda r: (r.band, -r.tier, r.key))
```

Mutating it to `(r.band, -r.tier, -r.weighted_score, r.key)` — score authority
re-entering as an intra-cell tie-break, exactly the mutation deferred minor
`E2-truth-core.md:3010(a)` predicted — leaves the **entire backend suite green:
4684 passed / 19 skipped**, byte-for-byte the same counts as the clean gate. The
deferred minor claimed the blind spot spanned "all 46 tests"; the true blast radius
is every test in the repository. The five ordering-relevant suites
(`test_layer_composition.py`, `test_result_grouping.py`, `test_grouping_cut.py`,
`test_facts_channel.py`, `test_chat_retrieval_parity.py`, 180 tests) were also run
in isolation against the mutation: all green.

**Failure produced:** the design's own stated property — "cell-membership rather
than score authority" (`layer_composition.py:661-663`, and the ordering contract at
`:897`, "``key`` is the sole [intra-cell discriminator]") — can be silently
inverted for every equal-`(band, tier)` cross-channel cell with no red anywhere,
including the door-parity suite. A future regression that reorders the served
envelope by score inside a cell ships invisibly.

**Disposition:** fix before merge, in the consolidated wave. The fix is one fixture
holding an equal-tier cross-channel pair plus one assertion that `key` alone breaks
the tie. Bundle `:3010(e)` (the `limit` test pins cut length, not that the cut
keeps the head of the total order) and `:3010(g)` (the `unsupported_action` ladder
position untested at runtime) into the same task — all three are the same shape in
the same suites.

### F2 — Important — the merge gate's two measured-quantity arms are completion gates: they cannot go red on the number they name

**Verified against code.**

- `scripts/gate.sh`'s "extraction F1 bench (--algo-only)" arm runs
  `backend/scripts/extraction_bench/run_bench.py`, whose `main()` computes the
  P/R/F1 cells, prints them (`run_bench.py:304-311`) and returns with **no exit
  path conditioned on any value**. The arm can fail only on cache-miss, manifest
  mismatch (`assert_manifest_current`, `run_bench.py:115`) or a crash. The recorded
  G-B floors (entities 0.912, relations 0.883) exist in the ledger and are called
  "the recorded floors" by the bench's own comments (`run_bench.py:46,239`), but
  are enforced nowhere. An algorithmic change that collapses relation F1 to 0.5 —
  in exactly the post-LLM half `--algo-only` exists to exercise — keeps the floor
  green.
- The `--full` "retrieval eval" arm is the same shape:
  `backend/scripts/benchlib/run_retrieval_eval.py:622-638` returns 0 after any
  completed eval. A ΔMRR of −1.0 exits 0; the drift language in
  `_designed_state_note` (`:308`) is prose in a report a human must read.

The G-B verdict's dead-guard audit (ledger `:1253`) certifies the *numbers that
session measured*, resting on the manifest guard and scorer reproducibility — it
does not, and does not claim to, make the gate arm itself bar-enforcing. Between
evidence sessions, "GATE GREEN" asserts replay integrity, not F1 health, while
CLAUDE.md presents the command as "the merge gate" and every lane reads its green
as the floor. This is the epic's characteristic defect shape sitting on the most
prominent check in the repository.

**Disposition:** fix before merge, or record explicitly. Either (a) `--algo-only`
asserts the four aggregate cells against the manifest-recorded floor values with a
stated tolerance, failing loud (small change; the manifest already pins assembly
identity), or (b) the arm is renamed/documented as "F1 cache replay integrity" in
`gate.sh` and CLAUDE.md so its green is never again read as F1 health. (a) is
recommended; (b) is the honest minimum.

### F3 — Important — the harness's forbidden-database protection is one recorded hole plus two unrecorded siblings, and three destructive entry points have no guard at all

**Verified against code.** The recorded deferred minor (`E2-truth-core.md:3023`)
names the `?database=` query-param bypass of `run_promotion_metrics.py`'s
`_assert_not_forbidden` (`:88-109`, reads `make_url(url).database` — path-derived).
The branch-level picture is wider:

- **Same hole, second guard:** `harvest_l2_facts.py:113-114` (`bench_db_name`,
  `.split("?", 1)[0]`) feeds `assert_bench_db_allowed` (`:117`); and
  `run_gc_evidence.py:133` repeats the same path-only parse inline. Every guarded
  entry point in the harness shares the recorded bypass.
- **No guard at all on the destructive paths:** `bench_db.reset_bench_db()`
  (`bench_db.py:51-76`) executes `DROP SCHEMA IF EXISTS public CASCADE` against
  whatever `BENCH_DATABASE_URL` names, with no forbidden-name check anywhere on
  the path. It is reached by `run_smoke.py:241`, `run_retrieval_eval.py:468` and
  `run_contradiction_missrate.py:58`. `BenchDatabase` (`bench_db.py:99-138`)
  likewise: its only check is SQL-identifier safety (`:110`), not lawfulness, and
  its `reset()` drops the schema of an arbitrary URL. `scripts/gate.sh` passes
  `BENCH_DATABASE_URL` through by design (T2.76), so a stray export in a lane
  shell reaches the drop directly: `BENCH_DATABASE_URL=…/darkmem_test` destroys
  the pytest database mid-run; `…/darkmem` destroys the write-forbidden one.
  `backend/scripts/benchlib/tests/test_bench_db.py` asserts reset/registry
  behaviour only — no test would notice a guard's absence.

**Failure produced:** the exact misconfiguration the guarded runners were built to
refuse is accepted without a symptom by the three runners that do the most damage,
and the guards that exist all trust a derived name the connection does not.

**Disposition:** fix before merge, one small task: a single shared
`assert_lawful_bench_url(url)` in `bench_db.py` — `make_url` plus query-param
inspection (refuse any `database=` kwarg naming a forbidden database), applied at
module import (for `BENCH_DATABASE_URL`), in `BenchDatabase.__init__`, and adopted
by the three existing guard sites. This also closes recorded minor `:3023` for
free.

### F4 — Important (non-blocking) — the `verified` journal can silently starve G-C's measurement: `record_event` never raises, and the sole journaller never counts its row back

**Verified against code.** `record_event` degrades loudly-in-logs but never raises
(`app/services/events.py:146-156`, own SAVEPOINT). The single sanctioned writer of
`verified` events, `KnowledgeTripleRepository.set_verification_status`
(`app/repositories/knowledge_triples.py:661`, journal call at `:970`), commits the
rung transition regardless of whether the journal row landed and never verifies it
did. G-C's metrics are, by charter, "SQL over `events` alone"
(`benchlib/promotion_metrics.py`, CLAUDE.md), and no reconciliation of rung state
against journal transitions exists anywhere in the tree.

**Failure produced:** a journal-side failure — a broken monthly partition is the
precise failure class `events_ensure_partition` was engineered around — lets the
ladder move while the measurement substrate records nothing. T2.40's re-measure
then under-counts promotions, and the false-promotion audit loses the very
corroboration/dispute evidence it audits, with no symptom beyond a log warning
that is not gate evidence. The epic already owns the correct mitigation pattern:
`dream_undo` counts its own `undone` rows back and raises when short
(`dream_undo.py:228,379`) — "an undo that could not be journalled does not
happen." The one journaller whose rows are G-C's raw data does not use it.
`citation_reverify`'s sha-scoping was explicitly designed *around* this property
("self-healing … since `record_event` never raises"), which shows the hazard was
known at one consumer and not propagated to the other.

**Disposition:** not a merge blocker (G-C is open; no promotion record exists),
but it must be recorded as a clause on T2.40's re-measure alongside the vacuity
clause: either `set_verification_status` counts its journal row back the way
`dream_undo` does, or the metrics runner gains a state-vs-journal reconciliation
probe (facts at rung X vs journalled transitions into X, with `_write_born_rung`'s
already-documented exclusion applied). Without one of the two, the "SQL over
events alone" premise is unfalsifiable from inside the measurement.

### F5 — Minor — the anti-staleness roster guard carries its own stale count

`backend/tests/test_code_deriver.py:1445`: `_direct_job_registrations`'s docstring
says the derivation collects "exactly the roster CLAUDE.md calls 'the fourteen
live ones'" — the pinned `expected` set (`:1519-1526`) holds **fifteen** keys and
CLAUDE.md was corrected to "fifteen" on 2026-08-07. The binding-level scan itself
is sound (verified: it pins `Job(key=…)` bindings in `app/main.py` against the
set, so a deleted registration goes red); only the prose inside the guard built to
end this exact staleness shape went stale. One-word fix; fold into the wave.

### F6 — Minor — T0.19's "unreachable in practice" claim verified, and the failure is loud

**Verified empirically.** In a main checkout `git rev-parse --git-common-dir`
returns relative `.git` (reproduced), and `scripts/gate.sh:33-38` then computes
`MAIN_CHECKOUT` relative to the *invoker's* cwd, since the `cd "$REPO_ROOT"` at
`:110` happens after interpreter resolution. Reproduced: from a foreign cwd the
subshell yields an empty `MAIN_CHECKOUT`, `PY=/backend/.venv/bin/python`, and the
preflight fails **loudly** as `GATE BLOCKED` (exit 2) — the correct category
(environment, not red gate) with a confusing path in the message. From a linked
worktree `--git-common-dir` is absolute (reproduced against `.worktrees/
master-claim`) and the fallback resolves correctly, which is the case the fix
exists for. The recorded disposition stands.

---

## Scan audit (negative results, recorded so they are not re-derived)

The branch's AST-scan surface was audited for the lens's scan failure modes
(wrong binding, line-text matching, allowlist drift, vacuous file sets). These
scans were read closely and **hold**; several document their own mutation drills:

- `tests/_reachability_scan.py` — structural on all four routes, honest stated
  bound, `app_sources` floor assertion prevents vacuous file sets.
- `tests/test_dream_jobs.py` family scan — one-hop derivation is a stated
  contract; `skip_files` is exactly the umbrella; `DREAM_JOB_KEYS` derives from
  the umbrella, not a hand list; `main.py` exemption is by structural role.
- `tests/test_chat_retrieval_parity.py` RRF scans — binding-checked (all four
  binding forms), import-origin leg closes the re-export evasion, blind spots
  stated in the docstring rather than discovered.
- `tests/test_claim_serving_gates.py` — quantifies over every `.py` under `app/`,
  producer set pinned to two files, emission shapes widened through review;
  fail-closed record semantics separately tested (`gate_eligible is not True`;
  record file verified absent on this branch).
- `tests/honesty/test_human_only_confirmed.py` — scope-level scan that survives
  its own recorded constant-mutation episode; behavioural tests drive the doors.
- `tests/test_events_append_only.py` — per-child TRUNCATE guard asserted on
  every existing partition, not just the parent.
- `tests/test_code_deriver.py` import closure — transitive, loader-call aware,
  bound stated (F5's docstring slip notwithstanding).
- `scripts/benchlib/tests/test_promotion_bars.py` — pins bars by exact value;
  moving one is a visible two-file diff as CLAUDE.md claims.
- `verification_ladder.get_ladder_config` — clamp ordering documented and
  floor-first (`verification_ladder.py:202-223`); per-parameter measurement
  permission, never blanket.

The 19 backend skips were enumerated (`pytest -rs`) to rule out soft-skip rot
hiding load-bearing assertions; see the run note at the end of this file.

---

## Triage of deferred minors and parked rulings

### `E2-truth-core.md:3006` (T2.23/T2.13 cluster)

- **Dead caller-supplied `cycle_id`** — may stand; dead-parameter cleanup for the
  next touch of `dream_undo.py`.
- **Untested `created_at` floor clause** — may stand; the failure mode is a
  refused/missed undo (user-visible) or a wider partition scan (performance),
  neither silent.
- **Unpinned `_none` sentinel** (`dream_undo.py:626-632`) — may stand; verified
  still doubly inert (by-id reader never asks for it; null-counterpart sha cannot
  match).
- **Read-path guard perimeter excluding hybrid search** — may stand; consistent
  with the design's own statement that the tombstone is nomination-scoped and
  `supersede()` remains available to any caller.

### `:3010` (T2.43/T2.13 cluster)

- **(a) F3 order-inertness blind spot** — **upgrade to fix-before-merge**; proven
  suite-wide by mutation (F1 above).
- **(b) empty-text rerank warning unasserted** — may stand.
- **(c) article title-fallback untested** — may stand until T3.02 exists to
  produce it.
- **(d) plan §2.3 seam-signature divergence** — conditionally closed: its stated
  closure was "T2.58's brief must state the flagless seam or §2.3 be amended";
  T2.58 is done. The controller should confirm the brief states it (one-line
  check); if not, the §2.3 amendment is owed. Not a blocker.
- **(e) `limit` test pins cut length, not head-of-order** — bundle with (a).
- **(f) misleading stray-id refusal message** — may stand.
- **(g) `unsupported_action` ladder position untested** — bundle with (a); same
  shape, one runtime-precedence test.

### `:3013` (T2.12 cluster)

- **(1) Score-ordering mirror of I1 in Phase W** — **still open; T2.23 did not
  close it.** Verified: `memory_dream.py` applies actions in judged order
  (`_judge_pairs` preserves the score-sorted pair order from
  `generate_pairs:524`; `_apply` at `:1977` dispatches with no kind ordering), so
  a duplicate pair outranking a subsume pair still associates first within a
  cycle. End-state converges across cycles, so this remains a minor; the one-line
  fix (stable-partition subsumes before associates in the actions list) is cheap
  enough to take in the wave, but it does not block merge.
- **(2) `memory_crossrefs.related_memory_id` not counted by `_reference_counts`**
  — may stand; no later task made the column load-bearing.
- **(3) I3 after-side fallback unguarded, (4) journal `project` Phase-R read,
  (5) `pair_arm_skipped_reason` unasserted** — may stand as recorded.

### `:3023` (T2.51) — forbidden-database query param

**Superseded by F3 above**: the recorded instance is one door of five; two
guarded doors share the hole and three destructive doors have no guard. Fix in
the wave via the shared guard; the individual recorded minor closes with it.

### `:3025` (T2.61/T2.02) — `add_source` spares uninterpretable refs

May stand: documented at the minting site and pinned executably
(`test_the_minted_ref_matches_the_shape_the_backstop_trusts`). The write-door
hardening remains the right future shape; nothing on this branch made the
exposure load-bearing.

### `T0.19` (E0) — relative `--git-common-dir`

Verified (F6): the recorded "unreachable in practice, loud when reached" holds.
May stand.

### Parked rulings — checked applied, and my position

1. **Doc 10 §6 scoping key** (`9e9b0367`) — applied as ratified: §6 now scopes on
   `detail.file_path`, re-resolution keys on `symbol_key`, and CLAUDE.md's
   code-indexing section explicitly records the shipped sha-comparison deviation
   with its declared cost. The doc-vs-code divergence is deliberate and *written
   down where the code is described*, which is the honest configuration. No
   disagreement.
2. **G-C→G-D cross-edge** (`c510e8ae`) — applied: the ledger row carries the
   ratified precondition and the correction that the human-rejection arm is live
   with no judge on its path (`gate-ledger.md:536-548`). No disagreement.
3. **The vacuity clause** (M1, T2.40's entry) — correctly still open. **One
   addition argued, not a re-litigation:** F4 above is a second way the same
   audit can read clean while measuring nothing — not a vacuous numerator this
   time, but a silently incomplete substrate. T2.40's re-measure clause should
   rule on both together: `audit_clears` must be able to distinguish precision
   from inoperability *and* the events stream it reads must be reconciled or
   made write-verified before its zero means anything.

---

## Merge verdict under this lens

**Merge-ready only after one consolidated fix wave; nothing here requires
re-architecture.** Blocking items (all small):

1. **F1** — the equal-tier cross-channel fixture and tie-break assertion
   (bundling `:3010(e)` and `(g)`).
2. **F2** — floor enforcement (or explicit renaming) of the gate's F1 arm; same
   decision applied to the `--full` retrieval-eval arm.
3. **F3** — the shared lawful-bench-URL guard at the five benchlib doors
   (closes recorded minor `:3023`).
4. **F5** — the one-word docstring correction, riding any of the above.

Non-blocking but must be recorded before merge: **F4** as a clause on T2.40's
re-measure (journal completeness beside the vacuity clause), and the `:3010(d)`
one-line confirmation. Everything else logged-but-not-looped may stand as
recorded.

The scans, honesty suites and append-only guards this epic built are — with the
exceptions named above — genuinely mutation-hardened, and several carry their own
recorded drill episodes. The lens's characteristic defect was found not in the
scan layer but in the places nobody had yet pointed a mutation at: the composed
order's tie-break, the gate arms' exit codes, and the harness's own database
doors.

---

*Run note:* the full-suite mutation evidence for F1 is reproducible with:
mutate `layer_composition.py:1006` as shown, run
`cd backend && .venv/bin/python -m pytest -q` (observed: 4684 passed /
19 skipped, 204s), restore the file by copying back the snapshot. The 19 skips
were separately enumerated with `-rs` on clean source and are environmental /
producer-gated, with no ordering-relevant assertion among them.
