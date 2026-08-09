# E2 whole-branch review — invariant integrity (2026-08-08)

Lens: cross-cutting invariant integrity across the composed branch (`feat/e2-truth-core`
at `c510e8ae` vs `master` at `19c6450c`). Every claim below is **verified against shipped
code** unless explicitly marked inferred; guard suites named below were re-run during this
review, not taken from the gate transcript.

## Verdict per invariant

| # | Invariant | Verdict |
|---|---|---|
| 1 | Invariant 15 (dream-job family unreachable from capture/retrieval) | **Proved holds** |
| 2 | No cross-fingerprint joins on embedding tables | **Proved holds** |
| 3 | Idempotent re-extraction (strip-then-write; repo key-space sharing) | **Proved holds** |
| 4 | Lowercase names + `display_name` + `technologies` (all three properties) | **Proved holds** |
| 5 | REPLACES family as the supersession trigger, no predicate drift | **Proved holds** (structurally stronger than CLAUDE.md describes) |
| 6 | One-journaller rule for `verified` events | **Code coherent; CLAUDE.md's statement of it is false** (finding F1) |
| 7 | Fact layer moves by name AND id; fold on `ux_knowledge_triples_open`; expire-not-delete | **Proved holds** |
| 8 | Chat/search ranking parity on order, proven only at weight 0 | **Proved holds** |

### 1. Invariant 15 — holds

- Family scan (`tests/test_dream_jobs.py`): one-hop derivation off the umbrella's imports
  yields {`contradiction_scan`, `fact_lift`, `memory_community_detection`, `memory_dream`,
  `verification_recompute`} minus `job_registry`; whole-file exemption is exactly
  `dream_jobs.py`; `main.py` exempted only at the two structurally-matched lifespan nodes.
  Re-run: 19 guard tests pass.
- Detector scan (`tests/test_communities.py:1382-1467`): exemption pinned to exactly two
  files. Re-run: pass.
- Reports scan (`tests/test_community_reports.py:585-760`): the `memory_community_reports`
  exemption is, as claimed, file-scoped (Tier-C symbols only in
  `memory_community_detection.py`), symbol-scoped (`SAFE_REPORT_PROJECTION_SYMBOLS`
  anywhere; all-or-nothing per statement), and from-imports-only (exemption granted to a
  specific `ImportFrom` node, never to a module name in a file). Current importers
  conform: `memory_overview.py:80` and `topic_browsing.py:68` import only
  `report_status`/`REPORT_STATUS_READY` (verified pure — `memory_community_reports.py:201`
  is a plain function of stored columns); `memory_community_detection.py:79` imports the
  four Tier-C names; `pin_suggestions.py` names the module only in docstrings. Re-run:
  15 guard tests pass.
- Independent sweep for routes outside the scans' claimed coverage: the only dynamic
  imports under `app/` are `app/schemas/envelope.py:129` (bounded to `app.schemas.*`),
  `app/services/code_parser.py:282` (bounded to the `_GRAMMAR_MODULES` tree-sitter table),
  and the star-import `app/services/extraction.py:11` (of `extraction_clean`, not a
  forbidden module). No `getattr`-with-literal reach into a family module exists.

### 2. No cross-fingerprint joins — holds

The one genuinely new read pattern, `repo_entity_merge`, is clean: the candidate query
(`app/services/entity_merge.py:238-252`) joins `entities` to exactly one
`entity_embeddings__<slug>` child with an explicit `ee.fingerprint = :fp` predicate; the
query vector is read out of that same child (`:241`), and the probe
(`find_similar_entity`, `app/repositories/graph.py:24-75`) runs against the same child
table for the same resolved fingerprint passed at `entity_merge.py:945-951`. Both sides of
every cosine come from one child table; the pass writes no vector, and its only
cross-partition reach is the `ON DELETE CASCADE` on the loser's rows — deletion, not
comparison. The fingerprint is resolved by data (`resolve_read_fingerprint`), never
`llm_fingerprint()`. The other consumers this epic added (`relation_embeddings.py`,
`triple_embeddings.py`, `ppr_snapshot.py:196-210`, `memory_dream.py` Phase R canary,
`reembed.py`) each resolve one fingerprint per statement through `child_table`.

### 3. Idempotent re-extraction — holds

- Phase 5's strip runs inside savepoint B (`app/services/pipeline.py:663-685`).
- `assert_from_repo` (`app/repositories/graph.py:659-769`) wraps
  `strip_repo_assertions` + rewrite in one `begin_nested()` — the repo-side analog.
- The shared `(name, entity_type)` key space is safe in both directions: the memory strip
  preserves repo-asserted rows and the repo strip preserves memory-asserted rows via the
  mutual `NOT EXISTS memories / NOT EXISTS repositories` guards
  (`graph.py:566-575, 645-654`).
- `merge_entities` preserves it: memory_ids are unioned onto the survivor before the loser
  delete, and the stranded-relation check (`entity_merge.py:497-509`) fails the savepoint
  rather than letting the FK cascade destroy an unrepointed edge. Re-extraction of a
  memory that asserted the losing name converges onto the survivor through Phase 4's
  type-constrained probe under the same threshold (pinned against `pipeline.py`'s AST by
  `tests/test_repo_entity_merge.py`; suite re-run, 32 pass).

### 4. Lowercase + `display_name` + `technologies` — holds

- New writer `code_deriver.py:153-156` lowercases and stashes differing casing in
  `properties.display_name`.
- `entity_merge._merged_properties` (`entity_merge.py:394-408`) drops a `display_name`
  that no longer renders the surviving name — the two stay one fact.
- `_recompute_technologies` (`entity_merge.py:867-901`) covers exactly the memories whose
  entity set changed (`merged_memory_ids` = union of both rows' assertions); the
  `TECH_TYPES` skip is an equivalence, not a shortcut, and `IS DISTINCT FROM` keeps
  `touch_updated_at` from firing on untouched rows.
- All three column properties present: lowercase asserted at the read
  (`graph.py:825` `lower(name)`), denormalised whole-array assignment in Phase 5
  (`pipeline.py:737-749`), GIN index `ix_memories_technologies`
  (`migrations/versions/0001_baseline.py:191`).

### 5. REPLACES family — holds, and is now structurally single-sourced

The trigger predicate is **one** function, `is_supersession_trigger`
(`app/services/supersession.py:40-48`), imported by `pipeline.py:34` and used at both
sites (`pipeline.py:758`, `supersession.py:169`), resting on
`REPLACES_FAMILY`/`family_key` (`relations.py:23-35`). Drift between the two files is no
longer representable. Detector body matches the six documented conditions, including
lowercased targets and the `(created_at, id)` tie-break (`supersession.py:100-214`).
CLAUDE.md's "the predicate lives in both … and they must change together" describes the
pre-consolidation shape — stale in the benign direction (see F4).

### 6. One-journaller — code coherent; the contract sentence is wrong (F1)

Tree-wide, `record_event(event_type="verified")` has exactly two call sites, both in
`app/repositories/knowledge_triples.py`: `set_verification_status` (:970) and `ratify`
(:1068). `ratify` **cannot** route through `set_verification_status` (which refuses
`confirmed` by design, :855-860), so its own journal row is the only way a human
ratification appears in the ladder's history. The consumer accounts for it explicitly —
`scripts/benchlib/promotion_metrics.py:113-129` documents ratify as "a different writer"
and anchors `RATIFY_OUTCOME` — and `_write_born_rung`
(`knowledge_triples.py:307-379`) writes the born rung with no journal row and a
machine-writable-set guard, exactly as documented. The **code** composition is sound; the
**CLAUDE.md sentence** "set_verification_status is the sole writer of `verified` events"
is false against shipped code. Finding F1 below.

### 7. Fact layer moves by name AND id — holds

`_rename_facts` (`entity_merge.py:703-752`) moves endpoint ids, denormalised names, and
`triple_key` together, scoped by the id the merge owns. The collision path is a fact
merge (`_fold_open_facts`, :759-864) implementing exactly the contract:
keeper by verification rank then older `created_at` then smaller id, with **no**
verification column written; `fact_sources` moved (exact duplicates dropped, residue
deleted — never copied); serving heat summed; belief window unioned with NULL `valid_at`
dominating and `LEAST` on `stated_expiry`; the retired row **expired** via
`KnowledgeTripleRepository.expire` (:469-521 — writes `expired_at` under `FOR UPDATE`,
journals `expired` only on a real transition, never deletes). `article_citations.fact_id`
is a hard FK with no ON DELETE (`0001_baseline.py:733`), so expire-not-delete is
load-bearing and preserved. The fold's open-belief predicate
(`expired_at IS NULL AND invalid_at IS NULL`) matches `ux_knowledge_triples_open`'s
partial predicate verbatim (`0001_baseline.py:574-576`), so an expired duplicate carrying
the survivor's key cannot collide. `reference_time` is NOT NULL in the schema, so the
`LEAST` without a NULL case is safe. Edge ordering (fold-before-rename, partner-as-keeper,
re-query per row) was traced and decides every case I constructed uniquely.

### 8. Chat/search ranking parity — holds

`tests/test_chat_retrieval_parity.py` asserts on **order** (:244), on a corpus deeper
than a chat turn's arm window (:263), on fused-vs-semantic disagreement (:352), and — the
half CLAUDE.md's caveat requires — pins that an activated `confidence_rank_gamma` moves
the search surface and *not* chat (:303-350), so "parity only at weight 0" is asserted,
not just described. Re-run: 23/23 pass.

## Findings

**F1 — Important (contract drift, doc fix).** `CLAUDE.md` "Verified facts (L2)", the
"One journaller" paragraph: "`KnowledgeTripleRepository.set_verification_status` is the
sole writer of `verified` events" is **false against shipped code** — `ratify`
(`app/repositories/knowledge_triples.py:1068`) is a second, deliberate, sanctioned writer,
already recognised by `scripts/benchlib/promotion_metrics.py:113-129`. Failure mode: the
next consumer of the `verified` stream written against CLAUDE.md's sentence assumes one
call path and the applier's evidence payload shape on every row; ratify rows carry only
before/after. The metrics runner defends itself, but the contract file is what tasks read
first. Fix: amend the sentence to name both writers and ratify's two-key payload. No code
change.

**F2 — Minor (stale claim in a load-bearing docstring).**
`app/repositories/graph.py:791-793` (`prune_orphan_entities`): "the deriver has no
scheduled caller yet (T2.96), so in production the arrays are still empty" — stale on this
branch; T2.96 landed `code_deriver` wired at boot (`app/main.py:327-339`), and
`repo_entity_anchoring` / `repo_entity_merge` also populate/consume `repo_ids` in
production. Failure mode: a reader concludes the repo-liveness predicate is vacuous in
production and simplifies it away — the exact stale-sentence shape invariant 23 exists
for. One-comment fix.

**F3 — Minor (convergence churn, no invariant broken).** When two near-named,
same-typed entities are **both** repo-asserted (two repos each asserting one spelling, or
one repo asserting both), `merge_entities` deletes the losing name, but the losing repo's
next re-derivation re-mints it via the exact-key upsert (`graph.py:687-711`),
`repo_entity_anchoring` re-embeds it, and the next merge tick re-merges it. Steady-state
oscillation per reindex cycle: one entity row, one embed, one `merged` events row, one
relation repoint — and a window between derivation and merge in which the graph serves
the split node. Each individual pass is correct and idempotent (survivor rule keeps
converging on the same node), so this is cost/journal noise, not corruption, and
`names_distinct` bounds the affected population. Recorded so recurring `merged` rows for
one pair are not misread as a merge defect; a durable fix (e.g. a name-alias the deriver
consults) is a design decision for a future task, not a pre-merge change.

**F4 — Minor (benign doc staleness).** CLAUDE.md's supersession section still says the
trigger predicate "lives in both `pipeline.py` and `supersession.py` and they must change
together"; since the consolidation it is one shared function
(`supersession.is_supersession_trigger`, imported at `pipeline.py:34`), which closes the
drift risk the sentence warns about. Amend alongside F1.

No Critical findings. No secrets, run data, or machine-local scratch were found committed
under this lens's files.

## Triage — deferred minors and parked rulings

Re-verified against the shipped tree, not the recording rows.

- **`E2-truth-core.md:3006` cluster (T2.23/T2.13).** All four may stand.
  The `_none` sentinel is confirmed still unpinned (`dream_undo.py:632`, no test names
  it) and confirmed doubly inert as recorded. The dead `cycle_id` parameter and the
  untested `created_at` floor (consequence: a full partition scan, perf not correctness)
  may stand; fold tests into the next touch of their files. The read-path guard's
  perimeter excluding hybrid search is compensated tree-wide: the family scan covers
  `hybrid_search.py` like every file under `app/`, so the exclusion is belt-only.
- **`:3010` (T2.43/T2.13/T2.58/T2.55).** (a) — the F3 order-inertness guard's blind spot
  (no equal-tier cross-channel fixture, so a `-weighted_score` tie-break inserted after
  band and tier passes all 46 tests) — is the epic's characteristic
  "guard that cannot go red" on a serving-order contract three later tasks built on.
  **Recommend fixing in the consolidated wave** (one fixture pair); not a merge blocker —
  shipped ordering is correct today. (b), (c), (e), (g) may stand. (d) is a corpus-owner
  item (plan §2.3 vs the flagless seam T2.58 shipped); route to the owner, not the wave.
- **`:3013` (T2.12 five minors).** (1) verified **not** applied by T2.23: Phase W still
  applies actions in pair order (`memory_dream.py:1931-1941`), so the within-cycle
  subsume/associate transient stands exactly as recorded — end-state converges across
  cycles; may stand, with the one-line ordering fix folded into the next dream change.
  (2)–(5) may stand as recorded.
- **`:3023` (`_assert_not_forbidden` query-param bypass).** Verified still open:
  `run_promotion_metrics.py:88-101` reads only `make_url(url).database`, so
  `…/darkmem?database=darkmem_test` still reaches a forbidden database. The read-only GUC
  caps the blast radius at "measure a mid-DROP database and emit garbage", and the shape
  requires deliberate construction. May stand; a one-line refusal of a `database` query
  key is cheap if the wave runs anyway.
- **`:3025` (`add_source` spares uninterpretable refs).** All three producers in the tree
  (`fact_lift.py:555,930`, `human_adjudication.py:277`) are the sanctioned ones and the
  minted-ref shape stays pinned by test; no new direct-ref producer landed on this branch.
  Correctly left alone.
- **T0.19 (`--git-common-dir` relative path).** Verified in `scripts/gate.sh:22-40`: the
  hazard is reachable only when `backend/.venv` is missing, and the empty-`MAIN_CHECKOUT`
  arm additionally requires invoking the script from outside the repo root; every arm ends
  in a loud missing-interpreter failure, never a silently green gate. "Unreachable in
  practice" holds; correctly left alone.
- **Parked ruling 1 (doc 10 §6 scoping, `9e9b0367`).** Applied coherently: §6 now scopes
  on `detail.file_path`; the shipped sha-comparison (`citation_reverify.py`) is a
  deliberate, CLAUDE.md-recorded deviation with its cost stated. Nothing owed.
- **Parked ruling 2 (G-C→G-D cross-edge, `c510e8ae`)** — docs-only ratification, present
  at HEAD. Nothing owed. **Ruling 3 (vacuity clause)** — open by design; owed by T2.40's
  re-measure, not by this merge.

## Merge verdict

**Merge-ready under the invariant-integrity lens.** All eight assigned invariants hold in
the composed branch — several are now structurally enforced rather than merely observed
(shared supersession predicate, threshold pin against the pipeline AST, partial-index
match between the fold and the schema). Nothing blocks.

Owed in the consolidated fix wave, none blocking: **F1** and **F4** (two-sentence
CLAUDE.md amendment), **F2** (one stale comment), and — recommended — the `:3010(a)`
equal-tier fixture plus the `:3023` one-line query-param refusal, both cheap while a wave
is running anyway. **F3** is recorded, not actioned.
