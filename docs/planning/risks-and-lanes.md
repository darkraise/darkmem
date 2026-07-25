# Dependency lanes and risk register

Two questions this file answers: **what can run at the same time**, and **what is most
likely to go wrong**.

---

## Part 1 — Dependency lanes

### The hard serialisation

Only four things in the whole plan strictly serialise. Everything else is a lane.

```
T0.12 (baseline migration) ──> most of E1
G-A  (T0.17) ──> E1 starts
G-B  (T1.50) ──> E2 starts
G-C  (T2.40) ──> code deriver lane (T2.27–T2.28)
G-D  (T2.41) ──> E3 starts
G-E  (T3.22) ──> F7 is "done"; Phase 4 opens on appetite
```

Gates are real barriers, not checkpoints to work through. Starting E2 before G-B means
building the truth core on a retrieval layer whose isolation is unproven — and every fact
count in E2 inherits that doubt.

### E0 — three independent lanes

| Lane | Tasks | Can run concurrently with |
|---|---|---|
| A — benchlib completion | T0.01–T0.05 | B, C |
| B — retrieval eval | T0.06–T0.10 | A (after T0.02), C |
| C — baseline migration | T0.11–T0.15 | A, B — **but serialises hard internally** |
| D — gate posture | T0.16–T0.17 | Needs A, B, C |

**Three agents can work E0 concurrently.** Lane C is the long pole and gates most of E1;
start it first.

### E1 — foundations first, then five parallel lanes

```
Lane A (LLM orchestrator + events, T1.01–T1.09)
   │  everything below journals to events or calls the orchestrator
   ├──> Lane B  capture + buffer      T1.10–T1.15
   ├──> Lane C  pipeline + graph      T1.16–T1.28
   ├──> Lane D  retrieval             T1.29–T1.35
   ├──> Lane E  lifecycle             T1.36–T1.37   (needs C: T1.21, T1.27)
   ├──> Lane F  code truth            T1.38–T1.41
   └──> Lane G  contract + UI         T1.42–T1.49   (each UI task needs its signal)
```

**Do Lane A first, alone.** It is nine tasks and it unblocks everything; running it
concurrently with consumers means rebuilding against a moving orchestrator.

After Lane A: **two to three agents, not four.** The original claim of four was checked
against the real backend layout and does not hold — the lanes are dependency-disjoint but
not *file*-disjoint:

| Collision | Files | Consequence |
|---|---|---|
| Lane C ↔ Lane D | `repositories/vector.py`, `repositories/graph.py` | T1.21/T1.26 and T1.29 rewrite the same repos. **Start D after T1.21 lands.** |
| Lane B ↔ D ↔ G | `api/routes/memories.py`, `api/mcp/server.py` | The capture doors, the `memory_reason` fix, and T1.42's envelope all edit them |
| Lane B ↔ Lane F | `app/main.py` | T1.13 and T1.40 both register jobs |
| Any schema task | the single baseline revision | Regenerating it concurrently conflicts every time — runbook §8 serialises these through one owner per epic |

Since tasks are commits on one epic branch and this repo has no remote, concurrent agents
need **separate worktrees** (`git worktree add`) and a rebase cadence, not just separate
task rows. Lane E waits on C; Lane G's tasks each wait on their specific backend signal,
so G interleaves rather than running as a block. Lanes I and J (the cutover and the
orphaned surfaces) run late: I is post-G-B by design, J after T1.58 flips demo mode off.

**The critical path through E1** is Lane A → Lane C (13 tasks, all the pipeline surgery) →
T1.50. Lane C is where the schedule lives; staffing it first is the highest-leverage
scheduling decision in the epic.

### E2 — the ladder is the spine

```
Lane A (facts + ladder, T2.01–T2.06)  ── the spine, everything else hangs off it
   ├──> Lane C  consolidation jobs   T2.08–T2.14
   ├──> Lane F  review/hygiene       T2.22–T2.24
   ├──> Lane G  judge (G-D)          T2.25–T2.26   ── independent, start early
   └──> Lane J  UI                   T2.36–T2.39
Lane B  projects registry  T2.07     ── independent, tiny, do it any time
Lane D  memory relations   T2.15–T2.17  ── needs Lane C's dream job
Lane E  topics             T2.18–T2.21  ── independent of the ladder entirely
Lane I  arm activations    T2.29–T2.35  ── independent; each is its own measurement
Lane H  code deriver       T2.27–T2.28  ── BLOCKED until G-C clears
```

**Start Lane G early.** The judge qualification (G-D) is on the critical path to E3 and
needs a hand-labelled gold set — the one task in this plan whose duration is a human
labelling bottleneck, not a compute one.

**Lane E (topics) and Lane I (arms) are genuinely independent** and good candidates for a
second agent running alongside the ladder work.

### E3 — two phases inside the epic

```
Lane A  articles     T3.01–T3.06   ── first
Lane C  inject       T3.09–T3.12   ── concurrent with A (independent)
Lane D  onboarding   T3.13–T3.15   ── concurrent
Lane E  checkpoints  T3.16–T3.18   ── concurrent (store half is Phase-1-capable)
   ↓
Lane B  F7 research  T3.07–T3.08   ── AFTER Lane A ships. Not concurrent.
Lane F  UI           T3.19–T3.21
Lane G  G-E          T3.22
```

**F7 is deliberately last.** See the fast-follow creep risk below.

### E4 and EH1

E4 is demand-gated and mostly serial behind T4.01. EH1 has one hard ordering rule:
**TH1.01 (define the faithfulness metric) precedes every other task in the lane** — that
ordering is doc 20 §4, not a preference.

### Concurrency ceiling

The practical limit is **three to four agents**, set by merge-conflict surface rather than
by dependencies. Two agents in the same lane will conflict; two in different lanes rarely
do. Lane assignment is the unit of parallelism, not the task.

---

## Part 2 — Risk register

### Carried from doc 20 §8 (the roadmap's own named failure modes)

| Risk | Why it bites | Mitigation | Watch for |
|---|---|---|---|
| **Gate starvation** — the gold sets behind G-C/G-D/G-F need human labelling and a solo maintainer is the bottleneck | Whole phases stall on one person's afternoon | Sets are deliberately small (the F1 bench is 26 memories and drove two quality campaigns); bars start conservative; the system **stays useful while gated** — candidates serve labelled, so a delayed promotion costs a label, never availability | T2.25 sitting in `todo` for weeks while E2 code piles up behind it |
| **Gate theatre** — a gate degrades into a checkbox under pressure | Silently reintroduces the intuition-driven shipping the corpus exists to prevent | Gates are numbers with stated bars in `config`, measured by harness runs; hard rules are structurally non-tunable — there is no knob to turn | A gate row in the ledger with a verdict but no measured number; a bar edited on the same day as the run |
| **Rebuild regression** — E1 rebuilds a working engine and drifts silently | The failure is quiet: extraction quality decays, scopes leak, nothing crashes | G-B's F1-parity-within-tolerance plus the zero-count isolation probe make the two highest-value regressions measured rather than reviewed-for | F1 drifting within tolerance repeatedly in the same direction — tolerance is not a budget to spend |
| **Horizon pull** — PKM and .NET are the tempting queue-jumps | Both are more fun than the committed path; both are firewalled precisely so deferring is free | Nothing in Phases 0–4 may depend on EH1/EH2 — a dependency in that direction is a Tier-3 amendment | Any E0–E4 task that references `documents`, `blocks`, or the .NET lane as a prerequisite |
| **Fast-follow creep on F7** | "Committed fast-follow" drifts into v1 scope; F7 is cheap *because* it follows L3 | Sequenced at the tail of E3 with the dependency argument attached; pulled earlier it re-opens the layer argument | T3.07 starting before T3.06 is done |

### Execution risks (this plan's own)

| Risk | Why it bites | Mitigation | Watch for |
|---|---|---|---|
| **`origin_key` gets it wrong in Phase 1** | Every corroboration count in E2 is `COUNT(DISTINCT origin_key)`. A too-generous resolution silently inflates every verification number downstream, and the error is invisible until facts are promoted that should not have been | T1.11 tests the merge-to-one rule explicitly; T2.02's test fails under row-counting | Any change to `origin_key` resolution after E2 starts — it is a Phase-1 decision with Phase-2 consequences |
| **Pushdown declared done without the probe** | Isolation is the one property everyone assumes and nobody measures | T1.29 and T1.35 are separate tasks on purpose: building it and proving it are different work, and the probe is Fable-tier and adversarial | T1.29 marked `done` while T1.35 is still `todo` |
| **Plan rot** — the plan and the code diverge silently | 156 tasks written in advance will be wrong in places; an agent that works around a wrong task instead of fixing it makes the plan progressively fictional | The amendment protocol makes updating the plan part of the task, and Tier 1 needs no permission | An empty amendment log after a dozen completed tasks — that is not a good sign, it means fixes are going unrecorded |
| **UI drifts ahead of its signal** | The frontend skeleton already renders demo versions of Phase-1, -2, and -3 surfaces. Shipping a surface over demo data reads as done | Every UI task's acceptance names the live backend signal it must bind to; principle 10 puts the surface in the same phase as its signal, not earlier | A UI task marked `done` whose backend task is still `todo` |
| **Arms activated on a flattering aggregate** | An arm that helps overall while destroying the paraphrase slice looks like a win | Retrieval eval reports per-slice always; the aggregate never replaces slices; activation needs the latency/cost twin | An activation-log row with an aggregate delta and no slice breakdown |
| **The inert set gets written to early** | T0.13 lands seven objects with no writer. A well-meaning task wiring one early breaks the scaffolding-not-substrate invariant and makes an unshipped thing look shipped | Each inert object names its first-writer task; a test asserts no writes | Any write before its named writer: `repo_ids[]` → T2.27, `documents`/`blocks` → TH1.02, `block_embeddings` → TH1.05, `triple_embeddings` → T2.33, `relation_embeddings` → T2.49, `article_embeddings` → T3.23, `events.api_key_id`/`actor` → T4.02 |
| **Three-database confusion** | A harness pointed at `darkmem_test`, or a test at `darkmem`, corrupts data or produces meaningless numbers | The runbook §7 states the rule; benchlib overrides `DATABASE_URL` before the first `app.*` import | Any new script importing `app.*` before setting its database URL |
| **Model tier chosen for cost, not fit** | A cheap model on an invariant-bearing task produces work that is expensive to detect and expensive to unwind | The runbook forbids downgrading a tier to save budget; cut scope instead | A Sonnet-tier commit touching pipeline phases, supersession, or fusion |
| **The cutover destroys data** | T1.51–T1.54 move the real homelab database onto the rebuilt engine. This is the only unrecoverable step in the plan, and the first draft had no task for it at all | Cutover runs **after** G-B, never before; T1.53 rehearses the whole thing on a `pg_dump` copy and proves the restore path, which doubles as the rollback; a fresh dump is taken immediately before the real run | Any attempt to reorder the cutover ahead of G-B "to test with real data" — that inverts the safety property |
| **A gate runner is written by the model that judges it** | Runbook §2 splits measurement design (Fable) from measurement plumbing (Sonnet/Opus) precisely so the number is not marked by its own author | The runners are separate Sonnet tasks: T2.44, T2.51, T2.52, T3.24, TH1.17 | A Fable gate task whose commit also creates its own runner script |
| **The recorded baseline goes stale** | G-B is parity against T0.05's numbers. If that model is deprecated or drifts between G-A and G-B, the tolerance becomes unmeasurable and the gate silently loses meaning | Record model, git sha, and fingerprint with the baseline; the LLM cache pins the outputs | A model deprecation notice, or an F1 delta that moves without a code change |

### Known-issue watchlist (already bitten once)

These are recorded root causes from this repo's history. Each is a regression that has
already cost a debugging session — the rebuild must not reintroduce them.

| Issue | The rule that prevents it | Bound to |
|---|---|---|
| Hybrid search returns string ids; the vector repo returns `UUID` — matches drop silently | Normalize at every boundary | T1.29, T0.07 |
| RRF and rerank scores computed then dropped at the API boundary | The trace must carry them all the way to the response | T1.33 |
| Mutual supersession made two memories vanish from the default view | The strictly-older `(created_at, id)` tie-break | T1.36 |
| TTL delete aborted the whole batch on the `superseded_by` constraint | Demote dependents before deleting | T1.37 |
| asyncpg `IndeterminateDatatypeError` on variadic ANY / unnest / jsonb | `CAST` every bound param Postgres cannot infer; roll back before mutating ORM objects in an error handler | Any raw-SQL task |
| Dedup merged distinct entities onto stale ghosts | `names_distinct` discriminator + the orphan sweep as backstop | T1.20, T1.28 |
| Prompt changes failed to move nuanced entity typing | Fix in the curated maps and the cleanup passes, not the prompt | T1.24, T1.27 |
| A LAN `421` "fixed" by disabling DNS-rebinding protection | Extend `MCP_ALLOWED_HOSTS`; never disable the check | T1.42, T3.13 |
