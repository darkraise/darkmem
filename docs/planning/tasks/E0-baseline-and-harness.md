# E0 — Phase 0: Baseline & harness

**Goal:** Land the single baseline migration with its dormant objects inert, and stand
the eval harness up as a first-class, gate-owning deliverable.

**Advance gate:** **G-A** — extraction F1 bench green reproducing the recorded as-is
baseline; retrieval eval running with accuracy + p95 latency + token cost; baseline
migration boots clean and boot-time reconciliation is idempotent (doc 20 §4).

**Epic branch:** `feat/e0-baseline-and-harness`

**Contract:** every task runs under [`../agent-runbook.md`](../agent-runbook.md).
Amendments go in the log at the bottom of this file.

**State of play (2026-07-25).** `backend/scripts/extraction_bench/` exists and works
(26-memory `gold.json` + held-out split). `backend/scripts/benchlib/` is **partially
built** — `bench_db.py` and `caching_llm.py` with tests exist; `ledger.py`, `corpus.py`,
`ingest.py`, and `run_smoke.py` do not. Six Alembic revisions exist; doc 19 collapses
them to one greenfield baseline.

---

## Lane A — finish the benchlib walking skeleton

Prior plan: `docs/superpowers/plans/2026-07-23-harness-benchlib-walking-skeleton.md`.
That plan's Tasks 1–2 are landed; these tasks complete it.

#### T0.01 — Append-only run ledger (`benchlib/ledger.py`)

`Model: Sonnet 5` · `Size: M` · `Depends: —` · `Doc: 17 §7` · `Tag: target-new` · `Gate: G-A`

**What.** A JSONL run ledger: `record(run)` appends, `read_runs()` replays. One line per
eval run, carrying run id, UTC timestamp, corpus id, fingerprint, git sha, metric
payload. Append-only — a run is never edited or deleted, so a regression is always
diffable against the run that preceded it.

**Done when:**
- [ ] `record()` appends exactly one line and never rewrites prior lines
- [ ] `read_runs()` round-trips every recorded field
- [ ] The ledger path is configurable and defaults under `backend/scripts/benchlib/runs/`
- [ ] A malformed trailing line (a killed run) is skipped with a warning, not a crash

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_ledger.py -q`

#### T0.02 — Corpus loader (`benchlib/corpus.py`)

`Model: Haiku 4.5` · `Size: S` · `Depends: —` · `Doc: 17 §3` · `Tag: target-new` · `Gate: G-A`

**What.** `load_corpus(path) -> list[entry]`, parsing a corpus JSON into validated
entries. Pure parsing — no DB, no pipeline knowledge. This task also **creates**
`benchlib/smoke/corpus.json` (the frozen 3-memory smoke corpus), which the first
acceptance checkbox presumes exists and which T0.04 consumes.

Validation must check **raw membership** against `ENTITY_TYPES` / `RELATIONSHIP_TYPES`.
`normalize_entity_type` and `normalize_relation_type` never raise — they silently rewrite
an unknown value to `concept` / `RELATED_TO` — so a loader that "validates" through them
validates nothing. Legacy aliases (`LEGACY_*_TYPE_MAP` keys, e.g. `framework`, `RUNS_ON`)
are untabled *for gold input* and must be rejected, not rewritten.

**Done when:**
- [ ] Loads `smoke/corpus.json` and the extraction bench's `gold.json` shape
- [ ] Rejects an entry missing `content` with a message naming the offending index
- [ ] Gold labels validate against the closed taxonomy — an untabled entity or relation
      type is a load error, not a silent pass (doc 17 §10, invariant 5)

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_corpus.py -q`

#### T0.03 — Offline ingest driver (`benchlib/ingest.py`)

`Model: Sonnet 5` · `Size: M` · `Depends: T0.01, T0.02` · `Doc: 17 §9` · `Tag: target-new` · `Gate: G-A`

**What.** Compose bench DB + caching LLM + the **real** `ProcessingPipeline`: construct
`ProcessingPipeline(caching_llm, bench_session_factory)` and call `process_batch`. The
harness must measure the shipping pipeline, never a reimplementation of it.

Two facts the original wording missed. First, **the cache must wrap `embed_batch`, not
`embed`** — `process_batch` reaches embeddings only through `embed_batch_chunked` →
`embed_batch` (`app/services/llm.py:224`, called at `pipeline.py:561` and `:686`), so
`caching_llm.py`'s original `embed`/`chat_completion` overrides left every embedding
uncached. Extending `caching_llm.py` is part of this task. Second, **`process_batch` only
enriches an existing `memories` row; it never inserts one** (`pipeline.py:373-390`), so
the driver must pre-create each row through the real `PostgresMemoryRepository` before
calling it. That is caller responsibility, not forked phase logic.

**Done when:**
- [ ] Runs a corpus end to end against `darkmem_bench` and returns per-memory outcomes
- [ ] Uses the real pipeline class — no forked phase logic in the harness
- [ ] Pins its gate configuration explicitly, so a flag flip elsewhere cannot silently
      change what the bench measures (doc 17 §9, the gate-state caveat)
- [ ] Records the active embedder fingerprint on the run; a run never mixes fingerprints
      (invariant 2)

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_ingest.py -q`

#### T0.04 — `run_smoke.py` and the affordability gate

`Model: Sonnet 5` · `Size: M` · `Depends: T0.03` · `Doc: 17 §7` · `Tag: target-new` · `Gate: G-A`

**What.** The human/CI entry point: reset the bench DB, ingest the smoke corpus twice,
and assert the second run makes **zero** live LLM calls. Freeze the ingestion-granularity
decision in `benchlib/FROZEN.md`.

**A zero live-call count is not on its own evidence of anything.** The gate must also
assert, per pass, that the pipeline did its work — outcome count equals corpus length, and
no outcome carries `error` in `embed` / `extract` / `vector` / `graph` or a non-null
`error`. Without that, a run in which every write silently failed reports `live LLM calls:
0` and exits 0. Do **not** assert `pass 1 live_calls > 0`: the cache is content-keyed, not
pass-keyed, so on a warm re-run pass 1 legitimately reads 0 and the gate would stop being
idempotent.

**Done when:**
- [ ] Second run issues zero live `embed` and zero live `chat_completion` calls
- [ ] The affordability assertion fails loudly if the pipeline reaches the model by any
      path the cache does not wrap
- [ ] `FROZEN.md` records the granularity decision (memory-per-entry) and the date
- [ ] The run appends to the T0.01 ledger

**Verify.** `cd backend && python scripts/benchlib/run_smoke.py` — expect a printed
`live LLM calls: 0` on the second pass.

#### T0.05 — Record the as-is extraction F1 baseline

`Model: Fable 5` · `Size: M` · `Depends: T0.04` · `Doc: 17 §3, 20 §4` · `Tag: exists-today` · `Gate: G-A`

**What.** G-A requires reproducing "the recorded as-is baseline" — which only exists once
somebody records it. Run the F1 bench against today's shipping extraction on both
`gold.json` and the held-out split, and write the four dimensions (entity name-only,
entity name+type, relation pair-only, relation full-triple) into the gate ledger as the
frozen reference point every later phase compares against.

**Done when:**
- [ ] All four dimensions recorded as precision/recall/F1, on both gold and held-out
- [ ] The run's git sha, model, and fingerprint are recorded alongside the numbers
- [ ] A stated **tolerance** for G-B parity is proposed with its reasoning (how much
      drift is noise vs regression) — this is the number Phase 1 is judged against.
      It must **anticipate T1.17's merged extract+classify prompt change**, which alters
      the extraction prompt and therefore the measured numbers; a tolerance set as if the
      prompt were frozen will read that planned change as a regression
- [ ] Written to `gate-ledger.md` under G-A

**Verify.** Both invocations, output pasted into the ledger entry verbatim. The bench
reads LLM config from the database, so the URL is required — and it must be
`darkmem_bench`, never `darkmem` (write-forbidden) or `darkmem_test` (pytest-only,
runbook §8). `run_bench.py`'s only database interaction is the read-only
`get_llm_config`, and the bench database's `llm_*` rows are transient (every benchlib
reset wipes them), so seed them first via `benchlib.run_smoke.seed_llm_purpose_configs`
with the key read from the environment:
```bash
cd backend
export DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench
export DEEPSEEK_API_KEY=<real key — never committed>
python scripts/extraction_bench/run_bench.py
python scripts/extraction_bench/run_bench.py --gold gold_heldout.json
```

---

## Lane B — the retrieval eval (target-new)

Starts after T0.02; the eval end (T0.09–T0.10) additionally needs T0.03's ingested
corpus. Independent of Lane C entirely.

#### T0.06 — Retrieval gold set + query-type slices

`Model: Fable 5` · `Size: M` · `Depends: T0.02` · `Doc: 17 §4` · `Tag: target-new` · `Gate: G-A`

**What.** Build the gold query→relevant-memory pairs, **sliced by query type**. The
slicing is the point: a flattering aggregate that hides a collapsed paraphrase slice is
exactly the dishonesty doc 17 forbids. Prior work (2026-04-16) found paraphrase, typo,
and fact slices weakest — start there.

**Done when:**
- [ ] All **seven** doc-17 §4 slices defined and documented — four query-type (exact,
      paraphrase, typo, fact) and three capability (multi-hop, temporal,
      knowledge-update). The capability slices are not optional: they are exactly what
      the Phase-2 arm activations must move to earn their flags
- [ ] ≥ 100 pairs total (doc 17 §11), with the count per slice stated
- [ ] Gold lives as JSON on disk (invariant 1 — no experiment-tracking service)
- [ ] Slice definitions are written down well enough that a later contributor can add
      pairs without drifting the definition

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_retrieval_gold.py -q`

#### T0.06a — Re-adjudicate the saturated multi-hop pairs

`Model: Fable 5` · `Size: M` · `Depends: T0.07` · `Doc: 17 §4` · `Tag: target-new` · `Gate: G-A`

**What.** T0.07's measured baseline showed the hybrid-only retriever **saturates** the
multi-hop slice: 13 of 14 pairs hit@10, MRR 0.946, and only `rg-0072` exhibits the failure
the slice was designed to produce. The cause is the one T0.06's review predicted — the query
names the consequence memory's domain, so the semantic channel reaches the second hop without
traversing the bridge. It is broader than the nine pairs that amendment named:
`rg-0067`, `rg-0068`, `rg-0071` and `rg-0075` also resolve semantically, at ranks 2, 3, 2 and 6.

A slice a hybrid-only baseline already wins cannot gate a graph-arm activation. Doc 00's
success criterion — retrieval "measurably beats a hybrid-only baseline on the multi-hop,
temporal, and knowledge-update slices" — is unmeasurable on multi-hop until this is fixed.

**Done when:**
- [ ] Every saturated multi-hop pair is retired-and-replaced under the `SLICES.md` discipline
      (retire in place, append the replacement, bump the gold version) — never rewritten
- [ ] Replacement bridges are chosen so the consequence memory is **not** semantically
      proximal to the query; the anchor entity must be the only route to it
- [ ] The replacements are verified against the warm cache: baseline hybrid-only rank of the
      consequence memory must be worse than K, measured, not argued
- [ ] `SLICES.md`'s multi-hop authoring rule gains that mechanical isolation check, so a
      future contributor cannot reintroduce a domain-naming query
- [ ] Re-measured baseline recorded, showing the slice now has headroom

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_retrieval_gold.py -q`,
plus the re-measured per-slice table from T0.07's runner pasted into the completion note.

#### T0.07 — Sliced accuracy scorer (MRR / hit@K)

`Model: Sonnet 5` · `Size: M` · `Depends: T0.06` · `Doc: 17 §4` · `Tag: target-new` · `Gate: G-A`

**What.** Score retrieval per slice and in aggregate. Report per-slice always; the
aggregate never replaces the slices.

**Done when:**
- [ ] MRR and hit@K per slice, plus aggregate, from one run
- [ ] The scorer normalises ids exactly as the pipeline does — hybrid search returns
      string ids, the vector repo returns `UUID`, and a boundary mismatch silently drops
      matches (`CLAUDE.md` cross-cutting invariants)
- [ ] A slice with too few pairs reports as under-powered rather than as a number

**Amendment (Tier-2, 2026-07-26, from the T0.06 adversarial review):**
- [ ] Before the multi-hop slice is trusted as an activation gate, measure the
      hybrid-only baseline's headroom on it: report baseline hit@K over the full
      relevant sets, checking rg-0063/0064, rg-0065/0066, rg-0069/0070,
      rg-0073/0074, and rg-0076 first — those queries name the consequence
      memory's domain, so the semantic channel may reach the second hop without a
      hop. T0.06 established lexical isolation only, not embedding-space
      isolation (`backend/scripts/benchlib/retrieval/SLICES.md`, multi-hop). If
      the baseline saturates the slice, the saturated pairs must be
      re-adjudicated (retire-and-replace) before any graph-arm verdict is read
      off it.
- Note for downstream supersession-aware evaluation (T0.10): supersession firing
  at ingest is wall-clock-dependent and not corpus-guaranteed — control the
  detector clock (`now=`) or re-date + re-adjudicate under retire-and-replace
  (SLICES.md, corpus authoring rules).

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_retrieval_scorer.py -q`

#### T0.08 — Latency and token-cost twin

`Model: Sonnet 5` · `Size: M` · `Depends: T0.07` · `Doc: 17 §2, §4` · `Tag: target-new` · `Gate: G-A`

**What.** Instrument p95 latency and token cost on every eval run. **Accuracy never
ships without its twin** — this is a doctrine, not a report field, so the runner must be
unable to emit an accuracy number without one. Note (Tier-2, 2026-07-26): the T0.05
extraction baseline was recorded before this instrumentation existed, so it ships
twin-less; the gap is recorded in its G-A ledger entry, and T1.17's merged-call cost
argument has no baseline twin to compare against at G-B.

**Done when:**
- [ ] p95 latency captured per channel and end to end
- [ ] Token cost captured per run, attributed by LLM purpose
- [ ] Emitting an accuracy number with no twin is a hard error in the runner, not a
      warning

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_twin.py -q`

#### T0.09 — Full-context baseline comparator

`Model: Opus 5` · `Size: M` · `Depends: T0.03, T0.08` · `Doc: 17 §4` · `Tag: target-new` · `Gate: G-A`

**What.** The comparison that makes retrieval numbers mean anything: the same gold
queries answered by stuffing full context, so every retrieval claim reads "as good as
full context at a fraction of the cost" — or admits it is not.

**Done when:**
- [ ] Full-context baseline runs over the same gold and emits the same metric shape
- [ ] Its own latency and token cost recorded (this is the expensive arm — the
      comparison is the argument for retrieval existing)
- [ ] Comparator output states both sides, never only the delta

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_full_context_baseline.py -q`
— the `run_retrieval_eval.py` entry point is T0.10's deliverable and does not exist yet.

#### T0.10 — Retrieval eval runner + dated report

`Model: Sonnet 5` · `Size: M` · `Depends: T0.09` · `Doc: 17 §4, §9` · `Tag: target-new` · `Gate: G-A`

**What.** One command that runs the eval, writes a dated report file, and appends to the
ledger. Reports are dated files on disk, not a service.

**Done when:**
- [ ] `run_retrieval_eval.py` produces `docs/eval/<date>-retrieval-eval.md`
- [ ] Report carries per-slice accuracy, the twin, the baseline comparison, git sha,
      fingerprint, and gate configuration
- [ ] Appends to the T0.01 ledger
- [ ] Two consecutive runs on an unchanged tree produce the same numbers (§7
      reproducibility — the content-hash seed path must hold)

**Verify.** `cd backend && python scripts/benchlib/run_retrieval_eval.py` twice; diff the
two reports' metric blocks — expect identical numbers.

---

## Lane C — the single baseline migration (doc 19)

Independent of Lanes A/B. **Serialises hard internally** — every task here depends on
the one before it.

#### T0.11 — Target schema snapshot + baseline design note

`Model: Opus 5` · `Size: L` · `Depends: —` · `Doc: 19 §2–§3, 04` · `Tag: target-new` · `Gate: G-A`

**What.** Before writing DDL: reconcile doc 04's target data model against the six
existing revisions and produce the explicit object inventory the baseline must land —
what carries over, what changes shape, what is new, and what lands inert. This is the
task that prevents the baseline from being an accident of migration history.

**Done when:**
- [ ] Every table, index, constraint, and partition template in the target enumerated
- [ ] Each marked `carries-over` / `reshaped` / `target-new` / `target-new, inert`
- [ ] Every inert object names the phase and the task that will first write to it
- [ ] SQL-first checked: no ORM-only construct is load-bearing anywhere (doc 20 §7)
- [ ] Written to `docs/planning/baseline-schema-inventory.md`

**Verify.** Inventory reviewed at Fable tier against docs 04 and 19 — every object
traced to an owning doc section, no unexplained entries.

#### T0.12a — Baseline part 1: core memory, graph, and taxonomy tables

`Model: Opus 5` · `Size: M` · `Depends: T0.11` · `Doc: 19 §2, 04` · `Tag: target-new` · `Gate: G-A`

**What.** The first pass over the **one** baseline revision file. `memories`, `entities`,
`entity_relations`, tags, `config`, `embedders`. Plain SQL.

**Note the file, not the revision count.** T0.12a–c are three passes building up a
**single** revision — the single-revision property is asserted in CI (T0.15) and is load
bearing. They serialise: a, then b, then c, one owner (runbook §9).

**The chain is never two-headed.** Deleting revisions `0001`–`0006` belongs to *this*
task's commit, not T0.12c's. Doc 19 §2 collapses the brownfield chain into the baseline
and holds `alembic history` at exactly one revision for the whole greenfield window, so
there is no sanctioned moment at which the baseline and the old chain coexist. A baseline
committed beside the six gives Alembic two heads, and `alembic upgrade head` — which both
`backend/tests/conftest.py` and `backend/scripts/benchlib/bench_db.py` shell out to when
they build their databases — fails outright on an ambiguous head.

**T0.12a and T0.12b are floor-exempt (runbook §4).** From this commit until T0.12c the
baseline is deliberately incomplete, so the backend suite cannot pass and its failure
carries no information. The floor is asserted once, by T0.12c, against the finished
baseline. That exemption makes the three passes **one atomic unit for merge purposes**:
run them on a lane branch off the epic branch and merge only once T0.12c is green, so no
other lane ever rebases onto a partial schema (runbook §6).

**Done when:**
- [ ] The named tables, their constraints and indexes exist from empty
- [ ] `chk_superseded_has_pointer` present and enforced
- [ ] Plain SQL — no ORM-only construct load-bearing
- [ ] Revisions `0001`–`0006` are deleted in this same commit, and `alembic heads` reports
      exactly one head

**Verify.** `cd backend && DATABASE_URL=$CHECK_URL python -m alembic upgrade head` on an
empty scratch database.

#### T0.12b — Baseline part 2: knowledge, code, jobs, and events tables

`Model: Opus 5` · `Size: M` · `Depends: T0.12a` · `Doc: 19 §2, 04` · `Tag: target-new` · `Gate: G-A`

**What.** Second pass over the same file: `knowledge_triples`, `fact_sources`, articles and
citations, `projects`, `repositories` and the `code_*` tables, job state, and `events` with
its partitioning.

**Done when:**
- [ ] All named tables exist with their constraints
- [ ] `events` is `RANGE(created_at)` partitioned (the trigger is T1.06's)
- [ ] Still one revision — no 0002 appears

**Verify.** As T0.12a, plus `alembic history` shows exactly one revision.

#### T0.12c — Baseline part 3: partition templates, indexes, full-suite green

`Model: Opus 5` · `Size: M` · `Depends: T0.12b` · `Doc: 19 §2–§3, 04 §5.3` · `Tag: target-new` · `Gate: G-A`

**What.** The GIN index on `memories.technologies`, the remaining indexes, and the proof
that the whole thing carries the existing suite. The four per-fingerprint embedding
templates land here as **registry entries** (`_TABLE_TEMPLATES` / `_AUX_INDEXES`)
exercised by T0.14's boot-time reconciliation — doc 19 §2 expressly rejects expressing
the child tables as static migration DDL, so nothing about them belongs in the Alembic
file.

**Done when:**
- [ ] All four templates present **as registry entries**, not as migration DDL (their
      inert labelling is T0.13's)
- [ ] The GIN index on `technologies` exists — supersession and retrieval both read it
- [ ] The **full backend suite passes** against a database built from the baseline alone —
      this is where the floor T0.12a–b were exempt from is actually asserted
- [ ] `alembic heads` still reports exactly one head: the six brownfield revisions went in
      T0.12a and nothing has re-chained behind the baseline since

**Verify.** `conftest.py` overwrites `DATABASE_URL`, so the suite needs `TEST_DATABASE_URL`:
```bash
PGPASSWORD=darkmem psql -h localhost -p 5433 -U darkmem -d darkmem -c "CREATE DATABASE darkmem_baseline_check;"
cd backend
export CHECK_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_baseline_check
DATABASE_URL=$CHECK_URL python -m alembic upgrade head
TEST_DATABASE_URL=$CHECK_URL python -m pytest -q
```

#### T0.13 — Dormant objects landed inert

`Model: Sonnet 5` · `Size: M` · `Depends: T0.12c` · `Doc: 19 §3, 04 §5.3` · `Tag: target-new, inert` · `Gate: G-A`

**What.** Land `repo_ids[]` on `entities`/`entity_relations`, the empty
`documents`/`blocks` tables, and all four per-fingerprint partition templates (block,
relation, article, `triple_embeddings`) — reviewed, frozen, **with no writer**.

**Done when:**
- [ ] Every object exists and is empty
- [ ] No code path writes to any of them — asserted by a test, not by inspection
- [ ] Each is labelled inert in the schema inventory with its future writer's task id
- [ ] The `repo_ids[]` amendment leaves the existing graph sweeps **byte-identical** in
      behaviour (doc 06 §6.1) — proven by the existing graph tests passing unchanged

**Verify.** `cd backend && python -m pytest tests/test_inert_objects.py -q`

#### T0.14 — Boot-time partition reconciliation, idempotent

`Model: Opus 5` · `Size: M` · `Depends: T0.13` · `Doc: 19 §2` · `Tag: target-new` · `Gate: G-A`

**What.** At every startup, loop the `embedders` registry and run the parameterised DDL
that guarantees each fingerprint's four child tables exist. Register-before-insert, and
idempotent — G-A explicitly names this.

**Done when:**
- [ ] Booting twice against the same database is a no-op the second time
- [ ] Booting against a database missing a child table recreates exactly that one
- [ ] Child tables are only ever named through `child_table(parent, fingerprint)` —
      never a literal (invariant 2)
- [ ] A malformed fingerprint slug is rejected at registration, not at DDL time

**Verify.** `cd backend && python -m pytest tests/test_boot_reconciliation.py -q` plus a
manual double-boot against a scratch database.

#### T0.15 — Freeze event + regeneration protocol

`Model: Haiku 4.5` · `Size: S` · `Depends: T0.14, T0.16` · `Doc: 19 §2` · `Tag: target-new` · `Gate: G-A`

**What.** Write down two rules, not one. First the rule that ends the regenerate-freely
window: after the homelab cutover (T1.54) the baseline is frozen and every later change is
an ordinary additive revision. Second — and this is the one every E1–E3 schema task needs
— **how to change the schema while the window is open**, because until the freeze the
baseline is a shared mutable file that several lanes will want to edit.

**Done when:**
- [ ] Both protocols documented: the freeze trigger, and the during-window rule that a
      schema change **regenerates the baseline** rather than appending revision 0002
- [ ] The during-window rule states that schema changes **serialise through one owner per
      epic** — concurrent regeneration of one file conflicts every time
- [ ] A CI assertion holds `alembic history` at **exactly one revision** until the freeze
      tag exists (doc 19 §2), wired into `scripts/gate.sh`
- [ ] `CLAUDE.md`'s migration section updated to match
- [ ] The freeze date is left blank until the cutover actually happens (no fictional date)

**Verify.** `rg -n "freeze" CLAUDE.md docs/planning/baseline-schema-inventory.md` and
`./scripts/gate.sh` — the single-revision assertion fails after a deliberate second
revision is added.

---

## Lane D — gate posture

#### T0.16 — Scripted merge-gate runner

`Model: Sonnet 5` · `Size: M` · `Depends: T0.10, T0.14` · `Doc: 17 §9` · `Tag: target-new` · `Gate: G-A`

**What.** There is no hosted CI — the gate is a *discipline, scripted*. One command runs
the whole floor so the posture is command-shaped and a future CI pipeline is a
transcription, not a design task.

**Done when:**
- [ ] `scripts/gate.sh` runs: backend pytest, frontend typecheck/test/build, and the F1
      bench in `--algo-only` mode
- [ ] Exits non-zero on any failure and prints which gate failed
- [ ] Takes a `--full` flag that additionally runs the retrieval eval and Playwright e2e
- [ ] Reaps every process it starts, including on failure

**Verify.** `./scripts/gate.sh` green; then break one test deliberately and confirm the
script exits non-zero naming that gate.

#### T0.17 — G-A evidence run and ledger entry

`Model: Fable 5` · `Size: M` · `Depends: T0.05, T0.16, T0.06a` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-A`

**What.** Actually clear G-A: run every gate probe, record the measured numbers, and
write the verdict. Adversarial — the job is to find the reason the gate should *not*
clear, not to confirm it.

**Done when:**
- [ ] F1 bench reproduces the T0.05 recorded baseline within its stated tolerance
- [ ] Retrieval eval runs and reports accuracy + p95 latency + token cost
- [ ] Baseline migration boots clean; reconciliation proven idempotent
- [ ] All three numbers, their artifacts, and the verdict written to `gate-ledger.md`
- [ ] If any probe misses its bar, G-A stays open and the shortfall is recorded — the
      gate is never argued around
- [ ] `CLAUDE.md` refreshed for anything Phase 0 changed (the collapsed migration chain,
      the harness commands) — runbook §1 makes it every agent's bootstrap contract

**Verify.** `./scripts/gate.sh --full` with output archived under `docs/eval/`.

---

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| 2026-07-26 | T0.12a, T0.12c | 2 | Moved deletion of revisions `0001`–`0006` from T0.12c's acceptance into T0.12a's; T0.12c now asserts the single head rather than creating it | As written, the baseline landed at T0.12a beside the six old revisions and they were only removed at T0.12c, leaving Alembic two-headed for two whole tasks. `alembic upgrade head` is how both `tests/conftest.py` and `benchlib/bench_db.py` build their databases, so every lane's test bootstrap would have failed on an ambiguous head. Doc 19 §2 forbids the coexistence anyway — one revision, always, until the freeze tag |
| 2026-07-26 | T0.12a, T0.12b | 2 | Declared both floor-exempt under runbook §4, and the a→c sequence one atomic merge unit to be run on a lane branch | Once the six revisions are gone at T0.12a, `alembic upgrade head` yields a deliberately partial schema until T0.12c completes it, so the repo-wide suite cannot pass. Runbook §4 admits no partial credit, so without a written exemption an honest agent stalls at T0.12a with a red floor it is not allowed to ignore and not able to fix |
| 2026-07-26 | T0.12a | 1 | Corrected the one-owner cross-reference from runbook §8 to §9 | §8 is environment facts; the serialise-through-one-owner rule is §9 |
| 2026-07-26 | (runbook §6) | 1 | `agent-runbook.md:172` said `progress.md` is "committed directly to `main`" | The same bullet's first sentence, and this repo's actual trunk, are `master`. There is no `main` branch; an agent following the second half of that sentence literally would create one |
| 2026-07-26 | T0.02 | 1 | Stated that T0.02 creates `benchlib/smoke/corpus.json`, and that closed-taxonomy validation must check raw membership rather than route through the normalisers | The first acceptance checkbox says the loader loads `smoke/corpus.json`, but no landed task created that file — a missing step. And `normalize_entity_type` / `normalize_relation_type` (`app/taxonomy.py:124`, `:154`) never raise; they fall back to `concept` / `RELATED_TO`, so a validator built on them silently rewrites bad gold instead of rejecting it, defeating invariant 5 |
| 2026-07-26 | T0.03 | 1 | Recorded that the LLM cache must wrap `embed_batch` (not `embed`), and that the driver must pre-create the `memories` row before calling `process_batch` | `process_batch` reaches embeddings only via `embed_batch_chunked` → `embed_batch` (`app/services/llm.py:224`), never `embed`, so `caching_llm.py` as landed left every embedding uncached and T0.04's zero-live-call gate was unpassable. And `_write_memory` (`pipeline.py:373-390`) only SELECTs and updates an existing row — there is no insert path — so a bare `memory_id` raises a FK violation from the vector upsert |
| 2026-07-26 | T0.04 | 1 | The affordability gate must also assert per-pass pipeline outcomes, not only the live-call count; and `bench_db` must forget embedder registrations across a reset | A stale process-wide `embedder_registry` singleton survived the bench-DB reset and silently broke pass 2's vector and entity writes while the live-call counter stayed correctly at 0 — the gate printed `live LLM calls: 0` and exited 0 over a pipeline doing no durable work. Verified by corrupting one cached chat response: before the fix the gate passed, after it the gate exits 1 naming the failing memory and step. Asserting `pass 1 live_calls > 0` was considered and rejected — the cache is content-keyed, so a warm re-run makes pass 1 legitimately free and the gate would fail on its second consecutive invocation |
| 2026-07-26 | T0.01-T0.04 | 1 | Recorded that a Sonnet-tier per-task review is not a substitute for runbook §6's Fable-tier adversarial review on a gate-feeding task | All four tasks carry `Gate: G-A`, so §6 requires an adversarial Fable-tier review. The Sonnet per-task reviews passed T0.01's ledger clean; the Fable adversarial pass then found a Critical in it (`read_runs` raised an uncaught `UnicodeDecodeError` on a truncated multibyte sequence, losing every prior good record and never healing) plus nine Important findings across all four modules. Both layers earned their place — the per-task review caught the T0.04 gate asserting only its live-call count — but the Fable pass is the one that must precede a gate claim |
| 2026-07-26 | T0.05 | 1 | Verify block now points at `darkmem_bench` (LLM rows seeded via `benchlib.run_smoke.seed_llm_purpose_configs`, key from `DEEPSEEK_API_KEY`), not `darkmem` | The real `darkmem` database has no schema on this machine and is write-forbidden to agents, so the Verify command as written could not run and nobody may make it run. `run_bench.py` only reads `get_llm_config` from the database, and runbook §8 designates `darkmem_bench` for eval runs; its `llm_*` rows are wiped by every benchlib reset, so seeding is an explicit step of the run |
| 2026-07-26 | T0.05, T0.08 | 2 | The G-A ledger entry now records that the T0.05 baseline ships without ledger rule 2's latency/token-cost twin, and T0.08's task text names the inherited gap | `run_bench.py` does not instrument the twin and modifying it was out of bounds for T0.05; the instrumentation is T0.08's deliverable. The cross-task consequence the plan missed: T1.17's cost-based justification for the merged one-call design has no baseline twin to compare against at G-B. An honestly recorded gap satisfies the ledger's spirit; a silent omission does not |
| 2026-07-26 | T0.05, T1.50 | 2 | The G-A entry records that the baseline's cache carries no response metadata (parsed extraction JSON only), and the G-B ledger section now requires the G-B runner to capture served-model metadata for its live re-record | `deepseek-v4-flash` is a vendor alias whose backing weights can rotate silently; with no `model` string or system fingerprint recorded at baseline, "silent vendor update" would be an unrebuttable escape hatch for any G-B shortfall. The requirement makes the tolerance's same-model condition checkable from the G-B side, the only side that still can |
| 2026-07-26 | T0.06a (new), T0.07 | 2 | Added T0.06a: the multi-hop slice must be re-adjudicated because the hybrid-only baseline already saturates it | T0.07's measured baseline put 13 of 14 multi-hop pairs at hit@10 (MRR 0.946), with only `rg-0072` failing as designed — and the cause is broader than the nine pairs T0.06's amendment named, since `rg-0067`/`rg-0068`/`rg-0071`/`rg-0075` also resolve the consequence memory semantically at ranks 2/3/2/6. A slice the baseline already wins cannot gate a graph-arm activation, so doc 00's multi-hop success criterion is unmeasurable until the pairs are replaced with bridges whose consequence memory is not semantically proximal to the query |
