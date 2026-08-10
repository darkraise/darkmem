# E3 whole-branch review — claims versus reality — 2026-08-10

**Branch:** `feat/e3-synthesis-and-reach`, 31 commits, reviewed at tip `26b0930e`.
**Lens:** claims versus reality (present-tense statements about producers that do not
exist or moved; invariant 23 — scaffolding must not read as shipped), plus the
mandatory triage of deferred minors and parked rulings, plus T2.115's execution —
the branch's largest unreviewed surface.
**Method:** every load-bearing claim was re-derived, not accepted — the retirement
draw, the assignment chain, the census arithmetic, the resample record and the
pinned suites were re-run or recomputed in this session; code-surface findings were
independently verified at the cited lines before being recorded here.

## Merge verdict: **BLOCKED** — one consolidated fix wave required

Two Criticals in the T2.115 execution (the measurement set that gates G-D, with a
re-measure running against it right now), one Important interop bug on the shipped
checkpoint surface, and a cluster of false present-tense claims — several minted by
this branch's own fix commits — on surfaces whose fix rounds were specifically about
honest present tense.

**Must fix before merge:**

1. **The T2.115 honesty wave (C-1, C-2, I-6, I-7, I-9, M-1, M-11).** Record the
   clause-5 composition deviation and the eg-0367 near-duplicate in LABELLING.md's
   History and the gate ledger **before the running G-D re-measure's verdict is
   recorded** — otherwise the record certifies a census property the file does not
   have. Owner adjudicates eg-0367's disposition (do **not** touch `gold.json`
   mid-attempt; the sha is what the running attempt is keyed on). Correct the wrong
   numbers and the non-reproducing reproduction command; commit the round's dispatch
   artifacts or record their loss.
2. **The checkpoint cluster (I-1, I-2, I-3).** Fix the MCP doors' hardcoded
   `source` (or get an owner ruling that the constant is intended and fix every
   comment that says otherwise); correct the three false `origin_key`-write-only
   claims; replace the tautological parity test with one that pins both doors.
   Pre-freeze is the cheap moment to fix a key-space divergence.
3. **The two invariant-23 texts (I-4, I-5).** `event-taxonomy.ts`'s "emitted for
   real / made both types live" and the Distribution tab's live curb card describing
   enforcement that does not exist. Text-only fixes.

**May land as recorded debt:** everything else below, including all parked minors
from the 2026-08-09/10 review rounds (triage in §4).

---

## 1. T2.115 execution — what was verified and what failed

### Verified by independent re-derivation (all hold)

- **Census:** 402 live pairs; contradicted pooled exactly 80, split 40 contacted /
  40 Rule-B at the unmoved `eg-0242` boundary. Both lattices exact (76/80, 38/40).
- **Retirement:** fully reproducible. `lattice_retirement.draw` over the committed
  pre-round file (sha `800d4d91…`) yields seed 2148355473, quota 8/4/3, and exactly
  the 15 ids marked `retirement_kind: "lattice"` in the shipped gold. The module
  landed in `c5a89999` *before* the draw executed, as clause 3 requires. Eligible
  pool 45 (contacted minus the 10 protected-core contradicted) confirmed.
- **Assignment chain:** the committed `round3_assignment.json` reproduces end to
  end — reconstructing the never-committed 336-pair intermediate state from
  committed data yields seed 547681360 and byte-identical slots; harvest capacity
  19/57 confirmed; the 9 `l2-fact` pairs sit verbatim on their anchored slots; all
  ten skips' grounds re-derived from the assignment and confirmed (3 symmetric
  RELATED_TO, 5 non-single-valued value-swap, 2 determined-duplicate).
- **Resample:** run file `2026-08-10-deepseek-v4-pro-58ac1a90.json` re-scored
  against the gold: n = 93, strata 80/6/7, exactly **one** disagreement (eg-0175),
  matching the embedded block. Certified sha re-derived: current gold minus the
  `resample` block hashes to `58ac1a90…`, and the draw seed 1487674000 =
  `int("58ac1a90", 16)`. The stale pre-round block was deleted at step 2 (C2 of the
  plan review, executed correctly). The three-sittings account is recorded rather
  than tidied, the *worse-looking* surviving sitting was kept, and `--from-raw`
  refuses a sha-mismatched raw. `performed_by` honestly names sitting 3 of 3.
- **Pinned suites:** 109 tests green across `test_entailment_gold`,
  `test_lattice_retirement`, `test_entailment_assignment`,
  `test_judge_qualification`; `DOCUMENTED_*_COUNTS` match the file; the
  `verdicts/` quarantine is test-asserted against `.gitignore`.
- **Rulings:** R1–R4 recorded in the ledger with the drafting/adoption distinction
  stated; budget lineage (4 cumulative attempts, resized sha starts at 0) recorded
  before any run could be the first to mention it. The rule-then-pairs rulings
  (Inception-window, Additional-value) are in the rulebook with their precedents.
- **The aiming question, structural half:** the retirement quota, seed and pool are
  pure functions of committed pre-round data (re-derived); the authoring slice
  quotas are mechanical; the 8 new value-swap pairs follow the rulebook's
  corpus-plausible-swap guidance with nothing visibly aimed in either direction;
  and the ledger's own finding that the per-pair miss census was uncomputable even
  for the contaminated controller closes the per-pair aiming channel for everyone.
  The eg-0367 near-duplicate (below) is itself evidence the authors were blind.

### C-1 (Critical) — the ratified rule's clause 5 is violated by the round that ratified it, and three in-tree claims say otherwise

Clause 5 (LABELLING.md, ratified in `f06c240c`): the pooled census of the affected
verdict class **"and its largest-remainder slice distribution are unchanged after
replacement."** Measured:

| pooled contradicted by slice | pre-round | shipped |
|---|---|---|
| value-swap | 42 | 42 |
| direction | 23 | 23 |
| temporal | 15 | **14** |
| overreach | 0 | **1** |

The retirement drew 8/4/3 (value-swap/direction/temporal); the authored
replacements landed 8/4/**2** plus one **overreach**-contradicted (eg-0405, the
Additional-value escalation), and the hand-authored temporal mix delivered 2C/3E/4U
against the committed target's own comment of "3 contradicted + 3 entailed + 3
unsupported" (`entailment_assignment.py:204`). The census still lands at exactly 80
— which means the verdict-class arithmetic was rebalanced around eg-0405's verdict
*after* authoring, and that rebalancing is recorded **nowhere**.

Claims contradicted by the shipped file:

- `48ad7e8e` commit message: "Fifteen retired, fifteen authored, **composition
  preserved**."
- `backend/scripts/benchlib/entailment_assignment.py:192-194`: "mirroring the
  retirement draw's quota so the pooled slice distribution is **unchanged end to
  end (rule clause 5)**."
- `entailment_assignment.py:204`: the temporal 3/3/3 comment.
- The plan v2 §6 table ("slices 8 value-swap / 4 direction / 3 temporal, mirroring
  the retirement so clause 5 holds") — superseded silently by execution.

The magnitude is one pair in 80. That is not the point: this corpus's whole
measurement discipline is that bright-line rules move only with a recorded owner
ruling, the rule was ratified as blocker B1 of this very round, and its first
execution broke it while every claim in the tree asserts compliance. The running
G-D re-measure will gate on a census whose composition the record misdescribes.

**Fix shape:** an owner-ratified deviation record (LABELLING History addendum +
ledger) before the re-measure's verdict is recorded; correct the three claims. Gold
surgery, if the owner wants the slice mix restored, must wait for the attempt to
finish and is a new lattice-rule question (eg-0405 is Rule-B population, which
clause 1 makes ineligible for lattice retirement — the rule as written cannot fix
what its first execution broke; the owner must rule).

### C-2 (Critical) — a semantic near-duplicate entered the contradicted census through the loophole the round itself documented

New pair **eg-0367** (`direction`, contradicted, l2-fact, slot 15): premise
`hv-27 has part scratch partition`, hypothesis "hv-27 is a part of the scratch
partition." Live pre-existing **eg-0093** (`direction`, contradicted): same
premise, hypothesis "The scratch partition has hv-27 as a part." — the **same
reversed proposition, reworded**. Three anchored direction slots sat on facts
already carrying a live direction pair; two collided byte-for-byte and were
skipped (slots 13, 28 → eg-0110, eg-0177), and the History records exactly those
two, adding the instruction "**do not resolve it by rewording the reversal** —
that passes the uniqueness check while leaving a near-duplicate in a measurement
set." Slot 15 is the third instance: the blind author's wording differed from
eg-0093's, the byte-uniqueness loader passed it, and the near-duplicate the rule
names as "worse than the collision it hides" is now **in the gated census**. The
History's "ten skips, all logged … the loader caught it" account is incomplete
against its own data.

Consequences: the 80-pair census contains 79 independent items (78 counting the
**pre-existing** eg-0194/eg-0251 duplicate — "Jenkins replaces GitHub Actions." /
"GitHub Actions is replaced by Jenkins." — which predates this branch and is
reported here as an adjacent finding). A judge that misses the hv-27 reversal
loses two of its four permitted misses on one fact; the bias direction is strict,
consistent with the round's "stricter surface" defense, but the lattice-exactness
argument the round exists for presumes 80 independent trials. Same fix sequencing
as C-1: record now, adjudicate disposition after the running attempt.

### I-6 (Important) — the round committed no dispatch artifacts, breaking both precedents

T2.54 committed 17 authoring/blind-pass artifacts
(`.superpowers/sdd/T2.54-entailment-gold-labelling/`); T2.110 committed 4
(`T2.110-gold-growth/`: dispatch, blind export, both pass outputs). **T2.115
committed zero** — no authoring briefs, no attestations, no adjudication pass
outputs. The History's firewall claims ("neither author read…, both … attested")
and the agreement rates (0.9848 / 0.9848 / 0.9697 — internally consistent with
64 adjudicated + 2 escalations, verified) are therefore prose with no committed
evidence, on the one round whose entire integrity case is the firewall. The brief
asked whether aiming can be shown either way; without the dispatched allowlists
and pass outputs it cannot, and with them it largely could. Fix: commit them if
they exist; otherwise record their loss in the ledger.

### I-7 (Important) — the companion quota executed is not the one the plan review approved, and the variant was chosen by the contaminated controller

Plan v2 §6 (Fable-reviewed, addressing I7 of the plan review) states the 51
companions as the **slice-marginal** largest remainder over the live
non-contradicted population: verbatim 6 / paraphrase 10 / weakening 8 /
**temporal 7** / direction 4 / overreach 10 / **unrelated 6** — re-derived this
session, those are the correct slice-marginal numbers. The executed
`ROUND3_SLICE_TARGETS` uses the **cell-level** (slice × verdict) largest remainder
— re-derived: temporal 6 / unrelated 7 — a different, equally defensible
algorithm, chosen by the contaminated controller and committed only in `48ad7e8e`
**together with the authored pairs** (the plan's "committed before authoring" holds
for the retirement module only). This is the plan review's I1 procedure-shopping
channel, applied to the companion quota, with no recorded amendment. Impact is
bounded (one slot, precision floor at 0.70 with measured 0.90 headroom, both
variants content-blind) but the round's zero-degrees-of-freedom claim is
overstated and the deviation from a reviewed plan is unrecorded.

### I-9 (Important) — wrong numbers and a non-reproducing reproduction command in the round's own record

- LABELLING History: "`l2-fact` **240** → 238 of 402 live" — the live series is
  **235 → 238** (pre-round live 235 recomputed; retired 6 l2-fact, added 9).
  Nothing in any state is 240.
- `entailment_assignment.py:257`: "(**248**/402 = 61.7%)" — reality is 238/402 =
  59.2% (the 248 assumes all 19 anchors landed; 10 were skipped). The History's
  own 59.2% is correct one file away.
- The History's clause-3 reproduction command
  (`python -m benchlib.lattice_retirement --verdict contradicted --n 15`) defaults
  `--gold` to the **current** file and therefore does not reproduce the draw
  (different bytes → different seed → different pool). It needs
  `--gold <gold.json at 48ad7e8e~1>`; as recorded, the one-command reproduction
  clause is unsatisfied.

### Minors in the T2.115 lane

- **M-1** — M1's T2.115 Done-when still says "`NEVER_CONTACTED_FIRST_ID` and
  LABELLING.md's range **move together**"; the executed ruling renamed the constant
  (`RULE_B_FIRST_ID`) and ruled it must **not** move. No amendment records the
  correction; the task text now contradicts the ratified behavior.
- **M-11** — "Ten skips, all logged": unlike both precedent rounds there is no
  per-slot skip log, only the aggregate sentence. The grounds check out when
  re-derived from the committed assignment (done here), but the record itself no
  longer supports that audit.
- **M-3** — `run_judge_qualification.py` prints the new "[2/4] per-pair verdicts"
  line after "[3/4] rendering report", a cosmetic step-numbering lie in the run log.

---

## 2. E3 code surfaces (claims vs reality, invariant 23)

Verified independently at the cited lines after a delegated sweep of the E3
surfaces.

### I-1 (Important) — `origin_key` "write-only over the wire" is false on the checkpoint doors, and the false claim was minted by the fix commit

`backend/app/services/checkpoints.py:29-30` and
`backend/app/api/routes/checkpoints.py:37-40` both state a client "can never learn
its resolved form" / it is "write-only over the wire" — while `serialize()`
(`checkpoints.py:218-227`) returns `origin_key` and `CheckpointResponse`
(`schemas/checkpoint.py:63`) serves it on both REST verbs and both MCP tools.
Every checkpoint response echoes the resolved key. Both claims arrived with
`ad19c53a` — the commit that (correctly) made the doors resolve instead of storing
verbatim — after which the pre-existing "no response echoes it" story stopped being
true. CLAUDE.md's origin_key section ("no response echoes it… write-only over the
wire") is now door-dependent: still true of capture, false of checkpoints. A
reader auditing corroboration-independence will mis-triage this door.

### I-2 (Important) — the MCP checkpoint doors hardcode `source` while claiming REST-twin resolution; cross-door lookups diverge

`backend/app/api/mcp/server.py:447-452` (and the `checkpoint_latest` twin at
~`:482`): comment "Resolved exactly as the REST twin resolves it" — code passes
`source=checkpoint_service.DOOR_SOURCE` unconditionally. The REST door
(`routes/checkpoints.py:41-43`) resolves via `X-Darkmem-Client` → User-Agent →
fallback. `checkpoints.py:78-83`'s "`DOOR_SOURCE` … is the *fallback*, not a
constant" is exactly a constant on MCP, and `ad19c53a`'s message ("each door
resolves `source` from its own transport") is false for MCP. Concrete failure: a
client declaring `X-Darkmem-Client: codex` saves `codex:<id>` over REST and
`checkpoint:<id>` over MCP — `checkpoint_latest` on one door silently misses the
other door's checkpoint, the exact wrong-context resume failure the module's
refusal machinery exists to prevent. `test_the_two_doors_produce_the_same_row`
matches on the sanitized tail and excludes `origin_key`, so no test sees it.

### I-3 (Important) — the cross-door parity test is a tautology

`backend/tests/test_checkpoints.py:432-441`
(`test_a_declared_identity_resolves_the_same_way_on_both_doors`) asserts
`resolve_checkpoint_origin(x, source="api") == resolve_checkpoint_origin(x,
source="api")` — f(x) == f(x). It drives neither door, passes under the pre-fix
verbatim-store implementation and under I-2's divergence alike, and its docstring
repeats I-1's false claim. The one test named for the property guards nothing —
this corpus's "test asserting a tautology" failure shape, verbatim.

### I-4 (Important) — the frontend event taxonomy claims the inject emitter is live; it is not

`frontend/src/features/activity/event-taxonomy.ts:8-10` ("T3.12 landed their
emitter"), `:57` ("all four below are emitted for real"), `:64-65` ("T3.12, which
made both types live"). Reality, stated correctly by the backend one module over
(`backend/app/services/inject_journal.py:26-27`): `record_inject` has **no
caller** — T3.10 is held by G-D; only `record_inject_curbed` is live (one caller,
`PUT /distribution/policy`). `test_inject_events.py:220`'s test name
(`…_now_that_they_emit`) repeats the overclaim. This is invariant 23's exact
mis-triage — a reader will believe inject rows exist to render — recreated by the
commit that made the *curb* event live.

### I-5 (Important) — the Distribution tab's live curb card describes enforcement that does not exist

`frontend/src/features/settings/components/distribution-tab.tsx:224-228`
(non-demo path): "One control, **applied on the server**: every target stops at
once. **Curbing clears each managed block to an empty marker pair**…" — no inject
writer exists (T3.10, G-D-gated); the route's own docstring
(`backend/app/api/routes/distribution.py:13-17`) says the flag "has exactly one
reader — the GET below" and that describing it as enforced "is the thing invariant
23 guards against". `use-distribution-api.ts:15` repeats the claim. Flipping the
curb today stops nothing and clears nothing. The text survived `b9293fcd` ("stop
the tab claiming what it does not know") — the fix round about exactly this.

### I-8 (Important) — `darkmem connect` plants tool configs in darkmem's own `backend/` and reports success

`backend/scripts/connect.py:8-12` documents "Run from `backend/`";
`connect.py:135` resolves `Path(adapter.mcp_config).expanduser()` against CWD. For
claude-code (`.mcp.json`), cursor (`.cursor/mcp.json`) and cline, the documented
invocation writes the config into `darkmem/backend/` — a workspace the user's
project sessions never read — then the handshake prints "connected". Success
reported for a wrong outcome is the same failure shape as this task's original
review Critical (the TOML merge). No `--workspace` argument exists. Fix: an
explicit target-dir argument or refusal for workspace-relative adapters.

### Minors (code surfaces)

- **M-2** — `.gitignore:29` (`docs/eval/*-retrieval-eval.md`, from `a2470dc7`
  whose message says "untracks"): nothing was untracked; three tracked eval files
  still dirty the tree when re-stamped (the stated motivation half-holds), and
  every *future* dated eval silently vanishes from `git status` — the docs/eval
  record-keeping habit ends without anyone deciding it. A policy change landed as
  an aside in an unrelated docs commit.
- **M-4** — `client_connect.py:64-72` `ConnectResult`: exported dead scaffolding,
  zero consumers, no note saying so — the same shape as NEW-4
  (`get_adapter_rejections`, deleted one fix round earlier).
- **M-5** — `connect.py` `main()` (argparse, `--dry-run`, file write, the
  `except OSError` DB-unreachable branch) has no test; whether asyncpg surfaces a
  refused connection as `OSError` (caught) or a wrapped SQLAlchemy error
  (uncaught traceback for the "entirely expected condition") is unverified.
- **M-6** — the extension options page offers a Server URL field while
  `manifest.json:10-12` grants `host_permissions` for `http://localhost:8000/*`
  only; a LAN base URL fails with the generic error. The narrow permission is the
  right posture; the un-caveated setting is the seam.
- **M-7** — `schemas/checkpoint.py:23-24,50`: "the two cannot disagree about any
  payload" overstates — `json.dumps` default `ensure_ascii=True` counts CJK at
  6 bytes vs JSONB's 3, and `pg_column_size` measures post-TOAST; the schema
  over-rejects (safe direction) but can 422 a valid payload citing a byte count
  that is neither its UTF-8 nor its JSONB size.
- **M-8** — `inject_adapters.py:172-180`: "a malformed override of a shipped tool
  leaves that tool served at its default" is true only for the non-dict shape; a
  well-typed-but-invalid override drops the tool from `adapters` entirely
  (default *not* in force). The wire stays honest; the comment's general claim is
  wrong for that shape.
- **M-9** — a declared origin that sanitizes to nothing (e.g. `":::"`) passes
  both checkpoint refusal guards and resolves to the shared key
  `"checkpoint:"` — degenerate declarations read each other's checkpoints.
  Contrived input; the "Unreachable while `declared` is non-empty" comment
  (`checkpoints.py:129-131`) covers only the other branch.
- **M-10** — `4f2e6919` (round-3 SDK fix: symbol-key/instance-attr escapes,
  `_mask_strings`, NEW-2 regression) is the branch's only code fix wave verified
  by **no** rescope. Light verification here: the probes now enumerate by kind
  (`Reflect.ownKeys`, `vars()` incl. instance probe), `get_adapter_rejections` is
  gone, doc 15 §6 is amended, and the gate is green at tip — but no adversarial
  pass drilled the new probes. Recommend a one-shot scoped rescope.

### Claims checked that HELD (coverage)

CLAUDE.md's three new claims (gate runs extension + both SDK suites + `make
build`; committed clients byte-compared against generator output; contract-refusal
in `generate.py`) all verified against `scripts/gate.sh:188-215` and
`test_sdk_generator.py`. SDK wire shapes match the REST contract (202 CaptureAck;
paginated search door; `with_trace` constant in both languages). Extension
no-auto-scrape: no content scripts, permissions allowlist-pinned, selection-gesture
only, ordinary door, hash-only dedupe. `article_eligibility` is claimed inert and
is inert (zero consumers; registered in the serving-gate roster). Events
vocabulary: taxonomy-first held for `checkpoint_saved`/`checkpoint`;
`checkpoint_saved`'s payload honors write-time minimization explicitly.
Checkpoints migration keeps the schema at ONE revision, matches the inventory,
201-not-202 argued and pinned. Distribution wire shapes match the frontend hook
exactly; parity-table exception recorded with its reason. Chat's
`label_suppressed` is served for real. The prior review rounds' fixes
(origin-resolution, CJK 422, demo-gating, budget-wipe, doc 15 §6 prose) are in
place. T2.115's mechanical spine — draw, assignment, census arithmetic, resample —
reproduces exactly.

---

## 3. The firewall question (brief §2)

No path was found by which the slice-level failure attribution reached an authored
pair: the quotas are pure functions of committed data (re-derived), the per-pair
miss census was uncomputable even for the contaminated controller (ledger,
verified reasoning), the value-swap pairs show rulebook-conformant construction
with no directional signature, and eg-0367 is itself blind-author evidence (an
informed author avoids the collision-adjacent premise). Two residual channels
remain open **as unverifiable rather than as leaks**: (a) the dispatch briefs and
attestations are uncommitted (I-6), so the allowlist-as-dispatched cannot be
inspected; (b) nothing in the record excludes controller-side edits between
authoring and landing — the mitigation is the blind adjudication, whose pass
outputs are also uncommitted (I-6 again). Committing the round's artifacts is what
converts "no path found" into "no path existed".

## 4. Triage — deferred minors and parked rulings

| Item | Where recorded | Verdict |
|---|---|---|
| **D-7** — eligibility lock does not bind the resample certification to pair content (no gold-sha/content hash in the block) | M1 amendment log 2026-08-09 | **May stand**, but T2.115 just re-paid the manual tax a third time (delete-block-then-recertify, plan-review C2). The stated fix (pairs-only content hash in the block, re-derived at eligibility time) should be minted as a task now; `--from-raw`'s sha refusal covers the raw record, not the embedded block. Not merge-blocking. |
| **D-8** — certification written into `gold.json` makes certified sha ≠ measured sha | M1 amendment log | **May stand.** Reproduced this round (certified `58ac1a90` vs on-disk `98fc4b49`); the ledger's lineage note is consistent with it. Same future task as D-7. |
| **T2.40 vacuity clause** (decidable-is-not-meaningful) | M1 amendment 2026-08-07 | **Stands untouched** — nothing on this branch made it load-bearing. |
| **T2.59 residue ruling** (journal payloads outlive deletion) | ledger | **Stands** — the branch's one new emitter (`checkpoint_saved`) explicitly honors write-time minimization; no new residue class added. |
| T3.01 minors ×5 (heat-arm coverage, pair-scoping test, `_INT_PARAMS` dead code, priority formula deviating from doc 09 §4.1, prose) | 2026-08-09 review | **Stand** — the module is G-D-gated with zero consumers. The doc 09 §4.1 deviation must be reconciled by T3.02 before productive use; note it in that task's brief. |
| T3.09 minors ×5 (blank-line accumulation, blocklist AST scan, exception naming, header quoting, CRLF) | 2026-08-09 review | **Stand** — writer is inert until T3.10; revisit there. |
| T3.11/T3.12 minors (cadence tripwire, payload allowlist, frontend-file assertion; the stale-docstring minor was fixed) | 2026-08-09 review | **Stand.** |
| T3.13 minors ×7 | 2026-08-09 review | **Stand**, except the config-placement seam which this review promotes to **I-8** (new evidence: documented invocation + success reporting). |
| T3.15 minors + adjacent doc defect; T3.16 minors ×5; T3.26 minors ×5 | 2026-08-09 reviews | **Stand** — M-6 and M-9 above are this review's additions in the same areas. |
| Fix-round N-8 (`CaptureAck.status` typed `string` not the literal) | 2026-08-10 rescope 2 ("pinned against nothing — deferred") | **Stands** — cosmetic typing; the runtime shape is pinned elsewhere. |
| NEW-3..NEW-7 (rescope 2's new minors) | 2026-08-10 rescope 2 | Claimed fixed in `4f2e6919`; NEW-4 and doc 15 §6 verified fixed here; the rest ride **M-10**'s recommended rescope. |
| `.superpowers/sdd/DEFERRED-MINORS.md` (E2-era list) | E2 | Out of this branch's scope; triaged by the 2026-08-08 E2 branch reviews. |

## 5. Adjacent findings (pre-existing, not this branch's defects)

- **eg-0194 / eg-0251** — a pre-branch semantic duplicate in the contradicted
  census ("Jenkins replaces GitHub Actions." / "GitHub Actions is replaced by
  Jenkins."), from the T2.110 round. Same disposition question as C-2; the owner
  should adjudicate both together. Similar non-census echoes exist in `direction`
  (eg-0042/eg-0104, eg-0127/eg-0189) — outside the recall census, lower stakes.
- `event-taxonomy.ts:57`'s "all four below" count was already stale on master
  (I-4 made the sentence worse, not first-wrong).
