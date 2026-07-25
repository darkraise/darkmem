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

`Model: Sonnet 5` · `Depends: —` · `Doc: 17 §7` · `Tag: target-new` · `Gate: G-A`

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

`Model: Haiku 4.5` · `Depends: —` · `Doc: 17 §3` · `Tag: target-new` · `Gate: G-A`

**What.** `load_corpus(path) -> list[entry]`, parsing a corpus JSON into validated
entries. Pure parsing — no DB, no pipeline knowledge.

**Done when:**
- [ ] Loads `smoke/corpus.json` and the extraction bench's `gold.json` shape
- [ ] Rejects an entry missing `content` with a message naming the offending index
- [ ] Gold labels validate against the closed taxonomy — an untabled entity or relation
      type is a load error, not a silent pass (doc 17 §10, invariant 5)

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_corpus.py -q`

#### T0.03 — Offline ingest driver (`benchlib/ingest.py`)

`Model: Sonnet 5` · `Depends: T0.01, T0.02` · `Doc: 17 §9` · `Tag: target-new` · `Gate: G-A`

**What.** Compose bench DB + caching LLM + the **real** `ProcessingPipeline`: construct
`ProcessingPipeline(caching_llm, bench_session_factory)` and call `process_batch`. The
harness must measure the shipping pipeline, never a reimplementation of it.

**Done when:**
- [ ] Runs a corpus end to end against `darkmem_bench` and returns per-memory outcomes
- [ ] Uses the real pipeline class — no forked phase logic in the harness
- [ ] Pins its gate configuration explicitly, so a flag flip elsewhere cannot silently
      change what the bench measures (doc 17 §9, the gate-state caveat)
- [ ] Records the active embedder fingerprint on the run; a run never mixes fingerprints
      (invariant 2)

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_ingest.py -q`

#### T0.04 — `run_smoke.py` and the affordability gate

`Model: Sonnet 5` · `Depends: T0.03` · `Doc: 17 §7` · `Tag: target-new` · `Gate: G-A`

**What.** The human/CI entry point: reset the bench DB, ingest the smoke corpus twice,
and assert the second run makes **zero** live LLM calls. Freeze the ingestion-granularity
decision in `benchlib/FROZEN.md`.

**Done when:**
- [ ] Second run issues zero live `embed` and zero live `chat_completion` calls
- [ ] The affordability assertion fails loudly if the pipeline reaches the model by any
      path the cache does not wrap
- [ ] `FROZEN.md` records the granularity decision (memory-per-entry) and the date
- [ ] The run appends to the T0.01 ledger

**Verify.** `cd backend && python scripts/benchlib/run_smoke.py` — expect a printed
`live LLM calls: 0` on the second pass.

#### T0.05 — Record the as-is extraction F1 baseline

`Model: Fable 5` · `Depends: T0.04` · `Doc: 17 §3, 20 §4` · `Tag: exists-today` · `Gate: G-A`

**What.** G-A requires reproducing "the recorded as-is baseline" — which only exists once
somebody records it. Run the F1 bench against today's shipping extraction on both
`gold.json` and the held-out split, and write the four dimensions (entity name-only,
entity name+type, relation pair-only, relation full-triple) into the gate ledger as the
frozen reference point every later phase compares against.

**Done when:**
- [ ] All four dimensions recorded as precision/recall/F1, on both gold and held-out
- [ ] The run's git sha, model, and fingerprint are recorded alongside the numbers
- [ ] A stated **tolerance** for G-B parity is proposed with its reasoning (how much
      drift is noise vs regression) — this is the number Phase 1 is judged against
- [ ] Written to `gate-ledger.md` under G-A

**Verify.** `cd backend && python scripts/extraction_bench/run_bench.py` — output pasted
into the ledger entry verbatim.

---

## Lane B — the retrieval eval (target-new)

Runs concurrently with Lane A after T0.03; independent of Lane C entirely.

#### T0.06 — Retrieval gold set + query-type slices

`Model: Fable 5` · `Depends: T0.02` · `Doc: 17 §4` · `Tag: target-new` · `Gate: G-A`

**What.** Build the gold query→relevant-memory pairs, **sliced by query type**. The
slicing is the point: a flattering aggregate that hides a collapsed paraphrase slice is
exactly the dishonesty doc 17 forbids. Prior work (2026-04-16) found paraphrase, typo,
and fact slices weakest — start there.

**Done when:**
- [ ] Slices defined and documented: at minimum exact, paraphrase, typo, fact, multi-hop
- [ ] Each slice has enough pairs for a stable number, and the count per slice is stated
- [ ] Gold lives as JSON on disk (invariant 1 — no experiment-tracking service)
- [ ] Slice definitions are written down well enough that a later contributor can add
      pairs without drifting the definition

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_retrieval_gold.py -q`

#### T0.07 — Sliced accuracy scorer (MRR / hit@K)

`Model: Sonnet 5` · `Depends: T0.06` · `Doc: 17 §4` · `Tag: target-new` · `Gate: G-A`

**What.** Score retrieval per slice and in aggregate. Report per-slice always; the
aggregate never replaces the slices.

**Done when:**
- [ ] MRR and hit@K per slice, plus aggregate, from one run
- [ ] The scorer normalises ids exactly as the pipeline does — hybrid search returns
      string ids, the vector repo returns `UUID`, and a boundary mismatch silently drops
      matches (`CLAUDE.md` cross-cutting invariants)
- [ ] A slice with too few pairs reports as under-powered rather than as a number

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_retrieval_scorer.py -q`

#### T0.08 — Latency and token-cost twin

`Model: Sonnet 5` · `Depends: T0.07` · `Doc: 17 §2, §4` · `Tag: target-new` · `Gate: G-A`

**What.** Instrument p95 latency and token cost on every eval run. **Accuracy never
ships without its twin** — this is a doctrine, not a report field, so the runner must be
unable to emit an accuracy number without one.

**Done when:**
- [ ] p95 latency captured per channel and end to end
- [ ] Token cost captured per run, attributed by LLM purpose
- [ ] Emitting an accuracy number with no twin is a hard error in the runner, not a
      warning

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_twin.py -q`

#### T0.09 — Full-context baseline comparator

`Model: Opus 5` · `Depends: T0.08` · `Doc: 17 §4` · `Tag: target-new` · `Gate: G-A`

**What.** The comparison that makes retrieval numbers mean anything: the same gold
queries answered by stuffing full context, so every retrieval claim reads "as good as
full context at a fraction of the cost" — or admits it is not.

**Done when:**
- [ ] Full-context baseline runs over the same gold and emits the same metric shape
- [ ] Its own latency and token cost recorded (this is the expensive arm — the
      comparison is the argument for retrieval existing)
- [ ] Comparator output states both sides, never only the delta

**Verify.** `cd backend && python scripts/benchlib/run_retrieval_eval.py --with-baseline`

#### T0.10 — Retrieval eval runner + dated report

`Model: Sonnet 5` · `Depends: T0.09` · `Doc: 17 §4, §9` · `Tag: target-new` · `Gate: G-A`

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

`Model: Opus 5` · `Depends: —` · `Doc: 19 §2–§3, 04` · `Tag: target-new` · `Gate: G-A`

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

#### T0.12 — The single baseline Alembic revision

`Model: Opus 5` · `Depends: T0.11` · `Doc: 19 §2` · `Tag: target-new` · `Gate: G-A`

**What.** Collapse the six revisions into one greenfield baseline written as plain SQL.
Regenerable freely until the homelab-cutover freeze event (T0.15) — this is the one
window where the schema can be rewritten rather than migrated.

**Done when:**
- [ ] One revision creates the entire target schema from empty
- [ ] `alembic upgrade head` on an empty database boots clean
- [ ] Plain SQL throughout — no ORM-only construct load-bearing
- [ ] The full backend suite passes against a database built from the baseline alone
- [ ] The old revisions are removed, not chained behind it

**Verify.** `psql -h localhost -p 5433 -U darkmem -d darkmem -c "CREATE DATABASE darkmem_baseline_check;"`
then `DATABASE_URL=...darkmem_baseline_check python -m alembic upgrade head && python -m pytest -q`

#### T0.13 — Dormant objects landed inert

`Model: Sonnet 5` · `Depends: T0.12` · `Doc: 19 §3, 04 §5.3` · `Tag: target-new, inert` · `Gate: G-A`

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

`Model: Opus 5` · `Depends: T0.13` · `Doc: 19 §2` · `Tag: rebuild` · `Gate: G-A`

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

`Model: Haiku 4.5` · `Depends: T0.14` · `Doc: 19 §2` · `Tag: target-new` · `Gate: G-A`

**What.** Write down the rule that ends the regenerate-freely window: after the homelab
cutover, the baseline is frozen and every later change is an ordinary additive revision.

**Done when:**
- [ ] The protocol is documented with the freeze trigger stated
- [ ] `CLAUDE.md`'s migration section updated to match
- [ ] The freeze date is left blank until the cutover actually happens (no fictional date)

**Verify.** `rg -n "freeze" CLAUDE.md docs/planning/baseline-schema-inventory.md`

---

## Lane D — gate posture

#### T0.16 — Scripted merge-gate runner

`Model: Sonnet 5` · `Depends: T0.10, T0.14` · `Doc: 17 §9` · `Tag: target-new` · `Gate: G-A`

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

`Model: Fable 5` · `Depends: T0.05, T0.16` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-A`

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

**Verify.** `./scripts/gate.sh --full` with output archived under `docs/eval/`.

---

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| — | — | — | (none yet) | — |
