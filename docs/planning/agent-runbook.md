# Agent runbook — the task contract

**Status:** living document, opened 2026-07-25. Every task in `tasks/` is executed
under this contract.

This is what an agent needs to pick up a darkmem task cold: how to bootstrap context,
which model tier to run at, what "done" means, what to do when the plan turns out to be
wrong, and when to stop and ask.

---

## 1. Bootstrapping a task

An agent starting a task has no memory of the session that wrote the plan. Do this
before writing any code:

1. **Read the task's owning design doc section.** Every task names one (e.g. `Doc 05 §3`).
   The task tells you *what* to build; the design doc tells you *why it is shaped that
   way* and which invariants bind it. A task is a pointer, never a replacement.
2. **Read `CLAUDE.md` at the repo root.** It is the business-logic baseline: the domain
   model, pipeline phases, taxonomy rules, and the cross-cutting invariants. A change
   that breaks one of its listed invariants is a behaviour change, not a cleanup.
3. **Search darkmem itself.** `memory_search` for the subsystem you are about to touch —
   past root causes and decisions are stored there and are frequently the difference
   between a fix and a re-fix.
4. **Check the epic's entry gate in [`gate-ledger.md`](gate-ledger.md).** An epic header
   names its *advance* gate — the one it must clear to finish. Its **entry** gate is the
   advance gate of the epic before it (E1 enters on G-A, E2 on G-B, E3 on G-D), and the
   task graph encodes it as a real dependency edge. **If that gate is open, stop** — the tasks below it are not startable
   yet, whatever their `Depends` field says. Gates are barriers, not checkpoints to work
   through: starting the truth core on an unproven retrieval layer means every fact count
   inherits that doubt. A task deliberately exempt from its epic's gate says so in its own
   text.
5. **Check `progress.md` for the task's dependencies.** If a `Depends` task is not
   `done`, stop: you are about to build on an interface that does not exist yet. A
   `Trigger:` field (rather than `Depends:`) means the task waits on a real-world event,
   not on other work.
6. **Claim the task** before starting — §6's claim protocol. One owner at a time.
7. **Read the existing code before changing it.** Most tasks are rebuilds of working
   subsystems. Match the surrounding idiom.

## 2. Model routing

Every task carries a **Model** field. The tiers, and what earns them:

| Tier | Use for | Signals |
|---|---|---|
| **Haiku 4.5** | Mechanical, fully specified, low-branching work. | Config rows and seed data; test fixtures against a stated shape; markup/CSS edits; mechanical renames; doc scaffolds; single-file additions with an explicit interface given. |
| **Sonnet 5** | Standard feature work against an established pattern. | One service method plus its tests; a REST route matching `api-rest-conventions.md`; a UI surface built on an existing component; a migration whose shape the task states; a JobRegistry job with a stated cron and config schema. |
| **Opus 5** | Cross-cutting or invariant-bearing work. | Pipeline phase surgery; retrieval fusion or SQL pushdown; the supersession and verification ladders; the baseline schema; anything touching more than three subsystems, or any task whose failure mode is a silent correctness drift rather than a crash. |
| **Fable 5** | Hardest reasoning, and adversarial verification of the above. | Designing a gate's metric and bar; judge qualification; false-promotion audit methodology; contradiction-veto semantics; reviewing an Opus-tier task before its gate is claimed; any Tier-3 amendment (§5). |

Three standing rules:

- **Escalate on discovery, never on difficulty of typing.** If a Sonnet-tier task turns
  out to touch an invariant, stop and re-run it at Opus. Note the escalation in the
  amendment log — a task whose tier was wrong is a planning signal worth keeping.
- **Measurement design and measurement plumbing are different tasks.** Where a task's
  acceptance is a number (any gate task), Fable designs the metric and the bar; Sonnet
  or Opus writes the harness code that produces it. Do not let the model that wrote the
  code also decide whether its number is good enough.
- **Never downgrade a task's tier to save budget.** If cost is a concern, cut scope or
  defer the task; a cheap model on an invariant-bearing task produces work that is
  expensive to detect and expensive to unwind.

### 2.1 Effort

Every task also carries an **Effort** field — `low` · `medium` · `high` · `xhigh` · `max`.
It is the **reasoning-effort setting the sub-agent is spawned with**: the `effort`
parameter on the dispatch, alongside `model`. **Pass it explicitly on every dispatch.** An
omitted `effort` inherits the controller session's, which is how a task silently runs
shallower or more expensively than intended. A controller that passes `model` and forgets
`effort` has routed half the task.

**Effort is independent of Model.** Every model runs at all five levels; the tier does not
imply the level and must never be used to derive it. They answer different questions:
Model asks *what does it cost the project if this is wrong*, Effort asks *how much
thinking does one turn of this work need*. A Haiku task can warrant deep reasoning and an
Opus task can be a mechanical edit to a dangerous file.

**The default is `high`.** Where nobody has determined a task-specific level, `high` is
what the field carries and what the dispatch passes. That is deliberate: an under-thought
turn on this corpus produces work whose failure mode is silent, and the cost of finding
that later dominates the cost of the extra reasoning.

**Review and adversarial verification run at `xhigh`.** That covers the per-task reviewer,
the scoped re-reviewer, the whole-branch review, and any task whose own text makes it
adversarial — the six gate evidence runs carry `xhigh` for exactly that reason, since each
is chartered to find the reason its gate should *not* clear.

**A level other than the default must be argued in the task's own text**, not inferred.
If a task genuinely needs `low`, `medium` or `max`, say why there, so the next reader can
check the reasoning instead of guessing at a convention. Escalate on discovery and log it,
exactly as with the tier: an effort field that turned out wrong is the same planning signal
a wrong tier is.

**Do not raise effort to compensate for a thin brief.** If a sub-agent needs more thinking
because it was told too little, the fix is the brief. Effort buys depth on a
well-specified problem; it does not buy context.

## 3. Task size, and what `L` obliges you to do

Every task carries a **Size**. It is orthogonal to both Model and Effort — a task can be
small and still need Opus, because tier tracks *consequence*, Effort (§2.1) tracks
*reasoning depth per turn*, and Size tracks only *how long the work takes*. T2.05
(human-only `confirmed`) is exactly that: `Size: S`, `Model: Opus 5`.

| Size | Time | Shape |
|---|---|---|
| **S** | ≤ ~2 hours | One file or function, a doc, a config row, a job registration. |
| **M** | ~2–8 hours, one focused session | A service method plus tests, a route, a UI surface, one pipeline phase. **This is the target size** — most tasks are here. |
| **L** | More than a day | Several mechanisms under one name, or bounded by something outside your control (a gold set needs human labelling). |

**An `L` task may not be executed directly.** Write a step-level plan first — the
repo convention is `docs/superpowers/plans/<date>-<slug>.md` — get it reviewed at Fable
tier, then execute the plan task-by-task. Starting to code an `L` task straight from its
acceptance criteria is how a week disappears into a branch nobody can review.

**If an `M` task turns out to be `L`, stop and say so.** That is a Tier-1 amendment: fix
the size field, split the task or write the step-level plan, and log it. A task that
silently runs long is the signal the plan was wrong, and it is worth more than the time it
costs to record.

## 4. Definition of done

A task is `done` only when **all** of these hold. There is no partial credit and no
"done pending review".

- [ ] Every **Done when** checkbox on the task is satisfied.
- [ ] The task's **Verify** command was actually run, and its real output is recorded in
      the completion note. Not "should pass" — the output.
- [ ] The repo-wide floor is green: `cd backend && python -m pytest -q` and, for any
      frontend change, `cd frontend && npm run typecheck && npm test && npm run build`.
- [ ] Any task touching the extraction surface additionally has
      `python scripts/extraction_bench/run_bench.py --algo-only` green (doc 17 §9).
- [ ] New behaviour has a test. New *invariant-bearing* behaviour has a test that fails
      if the invariant is removed.
- [ ] Every process the run started is dead (dev servers, test hosts, watchers).
- [ ] The work is committed in Conventional Commit form, one logical change per commit.
- [ ] `progress.md` is updated: status, commit sha, and a one-line note.

**The floor has exactly one sanctioned exception.** A task may be *floor-exempt* when it
is a mid-sequence checkpoint in an atomic multi-pass change to a single artifact, where
the intermediate state is deliberately incomplete and its failure therefore carries no
information (T0.12a–b, three passes building one baseline file). The exemption must be
written into the task's own text, and the pass that completes the sequence must assert the
floor for all of them. An agent never claims this exemption at run time — an unexpected red
floor is a finding, not a licence.

**Honest reporting is part of done.** If a check fails, say so with the output and leave
the task `blocked` or `in-progress`. A task marked `done` with a failing suite is the one
defect this whole corpus is built to prevent (invariant 14).

## 5. The amendment protocol

**Plans are living documents. An agent that discovers the plan is wrong is required to
fix the plan, not to quietly work around it.** Reality found during execution outranks a
plan written in advance — but the design corpus outranks both.

Three tiers, by blast radius:

### Tier 1 — correct it and log it

Task-local reality: a wrong file path, a missing step, a step that turns out
unnecessary, a task that should be split in two, an underestimated model tier.

**Do:** edit the task in its epic file, append a row to that file's **Amendment log**,
carry on. No permission needed.

### Tier 2 — correct it, log it, and surface it

The change reaches beyond this task: a newly discovered dependency between tasks, a task
that belongs in a different epic, changed acceptance criteria, a task that becomes
unnecessary because another task subsumed it, a new task the plan missed.

**Do:** edit every affected epic file *and* `progress.md`, append to the amendment log
with the rationale, and call the change out explicitly in the completion report so the
next scheduling decision accounts for it. Still no permission needed — but it must be
visible, never silent.

### Tier 3 — stop and escalate

The discovery contradicts the design corpus or the roadmap: a design doc is wrong or
ambiguous; a gate's definition or bar would have to change; phase order would have to
change; an honesty tag would have to be reclassified (e.g. calling something
`exists-today` that is actually `rebuild`); or an invariant would have to be relaxed.

**Do not proceed.** Write up what you found, what the doc says, and why they cannot both
be true, and stop. The divergence rule holds: the corpus doc wins until a human decides
otherwise. Tier-3 items are the ones worth a Fable-tier analysis before anyone answers.

### Amendment log format

Every epic file ends with a table. One row per amendment:

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| 2026-07-26 | Tx.yy | 2 | Split into Tx.yy + Tx.yyb; added a dependency the original ordering missed | *(illustrative row — replace with a real amendment)* |

## 6. Branch, commit, claim, and review

- **Branch per epic, not per task**: `feat/e1-engine-core`. Tasks are commits on it.
  A task large enough to want its own branch is a task that should have been split. A
  single agent works directly on the epic branch; concurrent agents each add one lane
  branch off it (below).
- **`progress.md` is canonical on `master`, not on the epic branch.** Otherwise the "live
  status" file forks per branch and no copy is true. Update it with a single commit
  touching only your own row, cherry-picked or committed directly to `master`. This repo has
  no remote, so concurrent agents share state through the working tree.
- **Claim protocol.** Claiming is one commit that sets your task's `Owner` and moves it to
  `wip`. If two agents race, the later commit loses and that agent picks another task —
  cheap, because the loser has done no work yet. Never start work on a row someone else
  owns.
- **Concurrent agents need separate worktrees, and therefore one lane branch each.** Git
  refuses to check the same branch out twice — `fatal: '<branch>' is already used by
  worktree at ...` — so "one epic branch, several worktrees" is not a reachable state.
  Branch each concurrent lane off the epic branch (`feat/e0-lane-c` off
  `feat/e0-baseline-and-harness`), one worktree each, merging back when that lane's last
  task is green. A lane whose *intermediate* commits break the repo floor must run this
  way rather than on the epic branch: the breakage stays on the lane branch and no sibling
  lane ever rebases onto it. See [`risks-and-lanes.md`](risks-and-lanes.md) for which
  lanes actually touch disjoint files, because several do not.
- **Conventional commits**, one logical change each:
  `<type>(<scope>): <subject>` — 50-char imperative subject, body explaining what and why
  at 72 columns. Scope is the subsystem (`pipeline`, `retrieval`, `frontend`, `harness`).
- **Reference the task id in the commit body**, not the subject: `Task: T1.12`.
- **Review before a gate, not before every task.** Per-task review at this volume costs
  more than it catches. What must be reviewed: every Opus-tier task, and every task whose
  output feeds a gate claim — reviewed at Fable tier, adversarially (try to refute the
  claim, not to confirm it).

## 7. When to stop and ask

Stop, do not improvise, when:

- A Tier-3 amendment surfaced (§5).
- A gate number lands below its bar. That is the gate working. Report the number; never
  re-run until it passes, and never widen the bar to fit the result.
- A task requires a credential, an external service, or a destructive operation on real
  data that the task did not explicitly authorise.
- Two design docs disagree with each other.
- The same task fails verification three times for different reasons — the plan, not the
  attempt, is probably wrong.

## 8. Environment facts an agent will need

Verified working commands (see `CLAUDE.md` for the full set):

```bash
# Backend tests — needs darkmem_test on the dev-compose Postgres (127.0.0.1:5433)
cd backend && python -m pytest -q

# Extraction regression bench (mandatory for extraction-surface changes)
cd backend && python scripts/extraction_bench/run_bench.py --algo-only

# Frontend gates
cd frontend && npm run typecheck && npm test && npm run build
cd frontend && npm run test:e2e          # Playwright, release candidates only

# Migrations (host-side runs must set DATABASE_URL — alembic.ini's URL is ignored)
cd backend && python -m alembic upgrade head

# Dev stack
docker compose -f docker-compose.dev.yml up -d
./scripts/start_dev_server.sh            # alembic upgrade + uvicorn :8000
cd frontend && npm run dev               # vite :3636, proxies /api /health /ws
```

**Three databases, three purposes, zero overlap** (doc 17 §9): `darkmem` (real),
`darkmem_test` (pytest, dropped and migrated every run), `darkmem_bench` (eval corpora).
A task that points a harness at `darkmem_test`, or a test at `darkmem`, is a defect
regardless of whether it passes. The one sanctioned exception is a **read-only** gate
probe measuring production behaviour (G-E's coverage distribution); it may read `darkmem`
and may never write to it.

**A fourth name is lawful and is not a leak: `darkmem_bench_t<sha10>`.**
`scripts/benchlib/tests/test_harvest_l2_facts.py` derives one per checkout from the
backend directory's hash, so the harvest reproducibility test's in-process double run
cannot collide with a sibling checkout or with the shared `darkmem_bench` under
`./scripts/gate.sh`. It is created on demand and **deliberately never dropped** —
re-migrating it every run would cost more than it saves. So it reappears after every
benchlib run, and dropping it is pointless rather than tidy: an agent chasing the
three-names rule literally will delete it repeatedly and report each deletion as
hygiene. (One did, three times, on 2026-08-08.) Leave it.

**`DATABASE_URL` does not point where you expect.** `conftest.py` unconditionally
overwrites it with `TEST_DATABASE_URL` — so setting `DATABASE_URL` in front of `pytest`
silently tests the wrong database. Set `TEST_DATABASE_URL` instead. And the derived
default resolves to port **5432** while the dev Postgres runs on **5433**, so any bare
shell command that reaches the database needs an explicit URL.

**The bench database has no per-lane isolation unless you ask for it.** `darkmem_test_N` is assigned per lane, but
`darkmem_bench` is one shared name — so two lanes running `scripts/benchlib/tests` concurrently collide and produce
failures that look exactly like a code regression (unrelated tests, moving between runs, in the one suite `pytest -q`
does not collect). **Set `BENCH_DATABASE_URL` to a per-lane database** (`darkmem_bench_<lane>`) whenever you run harness
work while other lanes are live. This cost three agents time in a single round on 2026-07-31.

**Commit before you drill, and never revert with a path-wide `git checkout --`.** A mutation
drill is edit → run → revert, and the revert is where work disappears. Two lanes lost
uncommitted source this way on 2026-08-02 — once a test fix, once an entire round of
review fixes — because a `git checkout -- <path>` written to undo the *mutation* also
undid every uncommitted change under that path. It is silent: the drill output looks
right, the follow-up run goes red for reasons that read like a real regression, and the
completion report describes code the tree does not contain. One lane caught it only
because a commit reported a test-file-only diff. So: **commit the work first, then drill**,
and revert by restoring a copy you made of the single mutated file rather than by asking
git to reset a path. Cheap discipline, and it is the difference between a green report and
a green report over missing code.

**Run tests in the foreground, one at a time, wrapped in an explicit `timeout`.** A lane
backgrounded its floor run and handed control back twice in one round, leaving two
concurrent runs against its own database; conftest drops the schema at session start, so a
collision produces failures indistinguishable from a real regression. If a command needs to
outlive a step, say so in the report rather than detaching and stopping — handing control
back mid-verification leaves nothing driving the work.

**The root cause was found on 2026-08-07 and it is mechanical, not a discipline problem.**
Six lanes stalled this way in one day, every one of them having read the paragraph above.
A shell command that runs past the tool's default limit is **auto-backgrounded**, and the
agent then stops with its work unverified and often uncommitted. Wrapping the command in
a `timeout` binary does not prevent this — the backgrounding is the *tool's* decision, not
the shell's. **Pass the Bash tool's own `timeout` parameter, set longer than the run needs
(the backend floor takes ~4–5 minutes, so 600000 ms is a safe floor for it).** Both are
worth doing: the tool parameter stops the auto-backgrounding, the `timeout` binary stops a
genuinely hung run from lingering. A lane that only does the second still stalls.

**Commit before every long run, not only before a mutation drill.** The stall itself is
recoverable — every one of the six was resumed with its work intact — but a lane that
stalls with nine modified files and no commits is one bad revert away from losing a whole
task, and that has happened twice for other reasons.

**A lane worktree has no `.venv`, no `node_modules`, and no bench cache — three
gitignored artifacts `git worktree add` never populates** (T0.19, T0.20). All three
are now preflight-checked by `./scripts/gate.sh` before any gate runs, and all three
report `GATE BLOCKED` (exit 2) naming what to install or restore, never `GATE RED` —
a lane's *code* did not break the SDK build or the F1 bench just because its tree is
missing an artifact:

- `backend/.venv/` — the gate detects when running in a worktree, falls back to the
  main checkout's interpreter (`/root/repositories/darkmem/backend/.venv/bin/python`),
  and prints which interpreter it resolved (`── resolved interpreter ──`) so you cannot
  silently gate against the wrong tree's code. The same fallback applies when you
  manually run the main checkout's interpreter by absolute path *from* your worktree's
  `backend/` directory, so imports resolve against your code rather than the main
  checkout's. `sdks/Makefile` used to hard-code its own
  `$(CURDIR)/../backend/.venv/bin/python`, a second interpreter path the gate's own
  resolution never reached — worktree-local and therefore always absent — which turned
  the "sdk build" gate red on a missing venv rather than blocked. The gate now passes
  its resolved `$PY` through (`env -C "$SDKS" PY="$PY" make build`); make's `?=` yields
  to an already-set variable, so the Makefile's default only applies outside the gate.
- `frontend/node_modules/` — run `cd frontend && npm ci`. This one already blocked
  correctly and was the model for the other two.
- `backend/scripts/extraction_bench/.cache/` (plus its `manifest.json`) — copy it in
  from the main checkout, or from a lane worktree that has already warmed it, before
  running the bench cold. The cache key is `sha256(content + system_prompt)`, so **any
  prompt change invalidates it**. The gate now preflight-checks for `manifest.json`'s
  mere existence and blocks if it is wholly absent; a manifest that exists but no
  longer matches the current extraction assembly (prompt/schema drift) is a real
  signal and still fails the gate red at the "extraction F1 bench" stage, not blocked.
  Before `--algo-only` can serve as a merge gate on a fresh worktree at all, someone
  must run the live pass — which needs both an explicit `DATABASE_URL` (the bench
  reads LLM config from the database) and a live extraction model:

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem \
  python scripts/extraction_bench/run_bench.py                      # live, warms the cache
DATABASE_URL=... python scripts/extraction_bench/run_bench.py --gold gold_heldout.json
python scripts/extraction_bench/run_bench.py --algo-only            # warm cache only
```

## 9. Changing the schema

The baseline is permanent since 2026-09-28 (owner ruling: deployed data is durable). Every
schema change is an ordinary additive revision, chained after the current head, that
upgrades a populated database in place.

- **Never edit `0001_baseline.py`.** `tests/test_schema_guard.py` pins its hash, and every
  deployed database carries that hash; `app/schema_guard.py` refuses to boot on a mismatch.
- **The chain is never two-headed, not even for one commit.** Every database bootstrap in
  this repo — `backend/tests/conftest.py` and `backend/scripts/benchlib/bench_db.py` —
  shells out to `alembic upgrade head`, which fails on an ambiguous head, and that failure
  takes down every concurrent lane. Two lanes that each add a revision must not both parent
  on the same head: the one that lands second rebases its `down_revision` onto the first.
  The gate and `test_the_revision_chain_is_linear_from_the_baseline` assert one head.
- **A revision carries the data.** Defaults or backfills for new NOT NULL columns, data
  moves for renames and retypes, drops only once no released code reads the object. The
  suite migrates an empty schema only; run the revision against a restored backup.
