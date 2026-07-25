# Plan review ledger — 2026-07-25

Three independent Fable-tier adversarial reviews of the planning corpus, run with
disjoint lenses so they could not confirm each other:

| Reviewer | Lens | Findings |
|---|---|---|
| **A — fidelity** | Every task verified against the design doc it cites | 18 |
| **B — completeness** | Every feature-epics story bullet traced to an owning task | 11 |
| **C — executability** | Dependency graph, verify commands, tiers, concurrency, runbook | 20 |

**49 findings.** Disposition below. `FIXED` = corrected in this pass. `ADDED` = new task(s).
`OPEN` = recorded, deliberately not fixed, with the reason.

The three converged independently on the same structural weakness: **work that belongs to
no lane**. The cutover, the deployment artifact, demo retirement, the measurement runners,
and the retrieval channels for facts and articles were each missed by the epic-shaped
decomposition, because an epic organised around *features* has no natural home for work
that happens once or serves everything.

---

## Blockers

| # | Src | Finding | Disposition |
|---|---|---|---|
| B-F1 | B | **No task for the homelab cutover.** Doc 19 §4's transform, the Tier-C re-extraction backfill, verification counts, the rehearsal-and-restore drill, and the freeze-tag application are unowned. The one point in the plan where irrecoverable user data is at stake, absent from tasks *and* the risk register. | ADDED — E1 Lane I (T1.51–T1.54) + risk row |
| C-1 | C | **Gates are not encoded in `Depends`.** Runbook §1.4 says "if a `Depends` task is not done, stop", but no E2 task depends on T1.50 (G-B) and no E3 task on T2.41 (G-D). An agent following the contract literally may start the truth core on an unproven retrieval layer. | FIXED — gate task added to each epic's entry-task `Depends`; runbook §1 gains an entry-gate check |
| C-2 | C | **T2.25's gold set is circularly defined.** It is "seeded from real synthesis drafts", but drafts come from T3.02 → T2.41 → T2.26 → T2.25. An agent picking it up cold has no source material; it deadlocks the G-D critical path. | FIXED — T2.25 now specifies the pre-gate draft source (manual non-shipping synthesis run against `darkmem_bench`, plus hand-authored pairs) |
| C-3 | C | **Schema-change protocol during the regenerable window is undefined.** T0.12 lands one baseline "regenerable until freeze", then E1–E3 create tables. An agent cannot know whether to regenerate the shared baseline, edit it, or add revision 0002 — and concurrent lanes regenerating one file is a guaranteed conflict. | FIXED — rule stated in T0.15 and runbook §8; schema changes serialise through one owner |

## High

| # | Src | Finding | Disposition |
|---|---|---|---|
| A-1 | A | **T1.11 tests the wrong mechanism.** The stated chain is doc 05 §2's `source` chain, not §2.1's `origin_key` chain (`X-Darkmem-Origin` header → `source:origin_id` → `unknown:source:project`). Doc 05 §12's "a per-request random is forbidden" was missed entirely. Every E2 corroboration count depends on this task. | FIXED |
| A-2 | A | **T1.01 assumes a data migration the corpus forbids.** Doc 11 §9.4 and doc 20 §10: greenfield + wizard re-run is the default; a transform only if trivial. | FIXED |
| A-3 | A | **T1.03 preserves a column its own dependency deletes.** `supports_embedding` lives on the provider table T1.01 drops; doc 11 §4 requires re-deriving the guard from `api_kind`. | FIXED |
| A-4 | A | **No task builds the facts or articles retrieval channels.** Doc 07 §2 makes both target-new; §5 fixes the four-layer composition (verified-above-labelled, disputed-both-sides, group-under-fact, cold-start labelling). E2 would ship facts nobody can retrieve. | ADDED — T2.42–T2.44, T3.23 |
| A-5 | A | **Four doc-08 mechanisms unowned:** the Tier-C `supersede()` primitive (§2.2), the status bridge (§3.4), demotion hysteresis + `under-sourced` (§4.3), and the enqueue-for-verification emit hook + no-op guard (§3.3, doc 05 §8.4). G-C measures machinery the plan never builds. | ADDED — T2.45–T2.47 |
| B-F2 | B,C | **Five gate runners exist only in `Verify` lines.** Nothing creates `run_promotion_metrics`, `run_coverage_distribution`, `run_faithfulness_gate`, `run_contradiction_missrate`, or the `--arm` interface. Where a Fable task implicitly owns its own plumbing, that violates runbook §2's measurement-separation rule. | ADDED — plumbing tasks at Sonnet tier; Fable tasks re-scoped to design + verdict |
| B-F3 | B | **The orchestrator rebuild ships with no UI.** Doc 13 §7 requires Settings→LLM become six inline purpose cards with the profile UIs *deleted*; leaving a profile picker over a schema with no profiles table is a named invariant-23 violation. The setup wizard and Flags tab are likewise unowned. | ADDED — T1.55–T1.57 |
| B-F4 | B | **No demo-mode retirement, and committed surfaces have no binding task.** `DEMO` defaults *on*; 64 files import `src/demo/`. Chat, Memory Graph, the Code section beyond two signals, Settings tabs, and the auth path have no task. The "UI drifts ahead of its signal" risk cannot catch surfaces with no task to watch. | ADDED — T1.58–T1.61 |
| B-F5 | B | **No deployment-artifact task, and T4.03 encodes the fallback as the target.** Docs 19 §5 / 18 §4: the target is app-as-edge — one image, `trust_proxy_headers` **off**, limiter on the transport peer; the nginx `X-Real-IP` path is the labelled fallback. | ADDED T1.62; T4.03 FIXED |
| B-F6 | B | **Nothing keeps `CLAUDE.md` true.** Runbook §1.2 makes it the bootstrap contract, yet E1 falsifies its LLM-config, events, capture, migration, and job sections. A stale bootstrap poisons ~150 downstream executions. | FIXED — refresh item added to each gate task's done-when |
| C-6 | C | **The tracker cannot coordinate.** No Owner column though the status vocabulary assumes one owner; branch-per-epic means the "live" file diverges per branch with no canonical copy; the rollup is hand-maintained arithmetic over 156 rows; the ~58 Fable reviews have no rows. | FIXED — Owner column, claim protocol, canonical-copy rule, review column |
| C-7 | C | **The mandatory bench floor fails cold.** `.cache/` is gitignored and `--algo-only` exits on any uncached content; the cache key includes the prompt, so any prompt change invalidates it. The live pass needs `DATABASE_URL` on port 5433 while the derived default is 5432. None of this is in runbook §7. | FIXED — runbook §7 corrected |
| C-8 | C | **T1.17 invalidates what G-B measures.** `run_bench.py` assembles its own call and does not go through the pipeline; once the merged prompt is the shipping default, the bench measures a non-shipping path — violating T0.03's own principle. | FIXED — done-when added to T1.17; T0.05 tolerance must anticipate the prompt change |
| C-9 | C | **Lane disjointness overstated.** Verified against the real backend: E1 Lanes C and D both rewrite `repositories/vector.py` and `graph.py`; Lanes B, D and G all edit `api/routes/memories.py`; B and F both register jobs in `main.py`. Same branch, no remote. | FIXED — concurrency claim reduced, shared-file list stated, worktree guidance added |
| C-10 | C | **T2.11 consumes the judge before T2.26 qualifies it**, contradicting T2.26's own "before any consumer's layer ships". G-C's audit would rest on an unmeasured adjudicator. | FIXED — dependency added |

## Medium

| # | Src | Finding | Disposition |
|---|---|---|---|
| A-6 | A | T1.29's query-plan checkbox is unsatisfiable for the semantic channel — doc 04 §10 / doc 07 §7 say HNSW applies the predicate as a *post-scan filter*; the win is correctness, not an index plan, and the fetch multiplier stays. | FIXED |
| A-7 | A | T2.34 would apply the memory TTL **delete** sweep to `knowledge_triples`. Facts are invalidate-not-delete and need no delete job; a dated fact gets its belief window *pre-closed*. | FIXED — split into memory-side and fact-side halves |
| A-8 | A | T0.06 names five slices; doc 17 §4/§11 fix **seven** (four query-type + three capability: multi-hop, temporal, knowledge-update) and ≥100 pairs. The capability slices are exactly what Phase-2 arm activations must move. | FIXED |
| A-9 | A | T2.31 tagged `activation`; doc 20 §5 and doc 07 §3 make `w_heat`/`w_recency` **target-new** (the `memory_access_stats` substrate is net-new). Tag drift is the invariant-23 class. | FIXED |
| A-10 | A | T1.14 contradicts doc 05 §2.2: `wait_process` is bounded by `buffer_wait_timeout_seconds` and **degrades to a plain 202** on timeout; it drives the flush synchronously rather than skipping the buffer write. | FIXED |
| A-11 | A | T1.13 binds the flush claim to the capture door's 1–100 cap; doc 05 §3 makes it `buffer_claim_batch` (default 32). §3.1's poison bounding, stale-claim visibility, and `done`-row retention are unowned. | FIXED |
| A-12 | A | T1.30 says RRF is "collapsed into one `rank_fusion_factor` formula"; doc 07 §3 keeps them separate — RRF fuses ranked lists, `rank_fusion_factor` is the post-fusion scalar multiplier. | FIXED |
| A-13 | A | Doc 10 §6's **citation re-verifier** (walks `fact_sources(kind='code')` whose `symbol_key` falls in a changed file set, marks stale, downgrades — never auto-expires) and the code-fact lifecycle are unowned. | ADDED — T2.48 |
| B-F7 | B | Two of four inert partition templates have no named first writer, making T0.13's done-when unsatisfiable: `relation_embeddings` (doc 19 §6's refresh job) and `article_embeddings`. | ADDED — T2.49, T3.24 |
| B-F8 | B | e2e coverage is assigned to tasks whose done-when never names the spec, so they can complete honestly without it; nothing creates the API e2e suite or the honesty specs. | ADDED — T1.64; done-when items added |
| B-F9 | B | Graph-arm activation measurement is folded into Opus-tier T2.32, so the model that builds the snapshot also judges its number. | ADDED — T2.50 |
| B-F10 | B | Doc 13 §2's `projectStore` / `contextStore` and the project switcher — the UI face of the T1.29 isolation work — have no task. | ADDED — T1.65 |
| C-4 | C | T0.09's `Verify` runs `run_retrieval_eval.py`, a script its own dependent task T0.10 creates — so T0.09 could never reach `done`. | FIXED — T0.09 verifies via a pytest file; T0.10 owns the runner |
| C-5 | C | Five gate/measurement scripts referenced only in `Verify` lines, with the Fable gate tasks as their only plausible owners — violating the runbook's own split of measurement design from measurement plumbing. | ADDED — T2.44, T2.51, T2.52, T3.24, TH1.17 at Sonnet tier |
| C-11 | C | T1.42's verify path `tests/test_mcp` does not exist (MCP tests are flat files); `Depends` omits the capture door it must expose; scope is several sessions. | FIXED |
| C-12 | C | T0.12's verify sets `DATABASE_URL`, but `conftest.py:11` unconditionally overwrites it with `TEST_DATABASE_URL` — the pytest half silently tests a different database. | FIXED |
| C-13 | C | Tier defects: T1.16, T1.19, T1.27 (pipeline phases / a cross-cutting invariant) and T2.05 (the human-only ceiling) are Sonnet where runbook §2 routes Opus. | FIXED |
| C-14 | C | T2.40 (G-C) can run with an empty `fact_sources` pipeline and measure a vacuous 0/0 — `fact_lift` is not in its dependency closure. | FIXED |
| C-15 | C | E3 bookkeeping: T3.09–T3.21 labelled `G-D` (their *entry* gate, already cleared) rather than G-E; T3.05 is a leaf so G-E can clear with staleness unbuilt; G-E measures "in production" while the e2e plan says nothing automated ever touches `darkmem`. | FIXED |
| C-16 | C | Frontend verifies cannot demonstrate their done-when: Playwright's `webServer` starts only vite, demo defaults on, and the named specs do not exist. | FIXED |
| C-17 | C | "The API e2e suite" is load-bearing in ring 3 but unlocatable; the real candidate (`docs/e2e/scripts/`) runs against a live server, not the pytest discipline the plan asserts. | ADDED — T1.64 |
| C-18 | C | T3.14 (SDK codegen, two languages, no generator named) and T3.15 (browser extension, three adapters) are each a sub-project in one task, with "proven by review" as acceptance. | FIXED — split |
| A-14 | A | Lane I gate fields say `G-C`; doc 20 §4 places arm activation, the `triple_embeddings` writer, and reranker-on as standing conditional gates *inside* phases. | FIXED |
| A-15 | A | T1.23 and T2.15 both own the memory-relation vocabulary; T1.23 omits doc 06 §3's `MEMORY_TYPES` 7→9 widening (+episodic, +procedural; `insight`/`profile` do not join) — a taxonomy-first, prompt-changing item. | FIXED |

## Low

| # | Src | Finding | Disposition |
|---|---|---|---|
| A-16 | A | T0.14 tagged `rebuild`; doc 19 §2 makes permanent boot-time reconciliation **target-new**. Doc 19 §2's CI assertion (`alembic history` = one revision until the freeze tag) has no home. | FIXED |
| A-17 | A | risks-and-lanes' inert watch list covers two of four templates; T1.29's `Depends: T1.16` contradicts the "Lanes C and D concurrent" diagram. | FIXED |
| C-19 | C | Non-task tokens in `Depends` ("all E1 lanes", "exposure trigger", "G-F appetite") cannot be evaluated by runbook §1.4's check. | FIXED — real edges named; `Trigger:` field introduced |
| C-20 | C | Stale environment facts: `spikes/` is actually `docs/design/spikes/`; T0.05's verify omits `--gold gold_heldout.json` though its done-when requires held-out numbers; gate-ledger says "harness CI" while the e2e plan says there is no hosted CI; UUIDv7 needs stdlib 3.14+ or the `uuid6` package against `requires-python = ">=3.12"`. | FIXED |
| A-18 | A | T3.17 cites "invariant 17" for the resume-budget behaviour where doc 20 §9 defines inv. 17 as two-front-doors. **Inherited from feature-epics**, which carries the identical citation. | OPEN — the plan is faithful to its spine; the misnumbering is in feature-epics and correcting it is a doc-04/20 question, not a plan defect |
| B-F11 | B | `topic_detection` job registration; detail-level acceptance not carried into E2/E3 UI tasks; the MCP-resource inject transport (matrix row, no home); backup cadence. | FIXED — except the MCP-resource transport, noted as a horizon stub |

---

## Remediation outcome (same day)

**156 → 188 → 204 tasks.** Round 1 added 32; the round-2 review (below) added a further
16 through splits and missed mechanisms. Every finding is either fixed in place or
recorded `OPEN` with its reason.

| Change | Detail |
|---|---|
| E1: 50 → 65 | Lane I, the homelab cutover (T1.51–T1.54). Lane J, the surfaces the rebuild orphans (T1.55–T1.65): Settings/LLM, the setup wizard, Flags, demo retirement, Code, Chat, Memory Graph, Activity, the app-as-edge artifact, Settings ops tabs, the API e2e suite, and the project/context stores. |
| E2: 41 → 53 | Lane L (T2.42–T2.53): the facts channel, four-layer composition, arm ablation, the `supersede()` primitive and status bridge, demotion hysteresis, the `sources_changed` emit hook, the citation re-verifier, `relation_embeddings`, graph-arm measurement, two gate runners, `topic_detection` scheduling. |
| E3: 22 → 26 | Lane H (T3.23–T3.26): the articles channel and `article_embeddings` writer, the coverage runner, and the SDK/extension scaffolds split out of oversized tasks. |
| EH1: 16 → 17 | TH1.17, the faithfulness runner split from its Fable gate task. |
| Tiers | 79/58/15/4 → 94/72/17/5. T1.16, T1.19, T1.27 and T2.05 promoted to Opus. |
| Tracker | Now **generated** from the epic files by `scripts/gen_progress.py`, so ids, titles, and tiers cannot drift from their tasks. Gained Owner and Review columns and a claim protocol. |

Verified after remediation: all 188 task references resolve to a defined task, no
duplicate ids, every task carries a model tier, and no non-task token survives in a
`Depends` field.

**Two findings changed the plan's own rules rather than a task.** The runbook gained an
entry-gate check (a gate is a barrier, not a `Depends` edge) and a schema-change protocol
for the regenerable window. Both were structural holes that no individual task could have
closed.

---

## What the reviewers checked and found clean

Recorded so the coverage is auditable rather than assumed:

- **Gate definitions** match doc 20 §4 verbatim, including the G-C→deriver consequence and
  G-G's harness-first conditions.
- **Phase order and dispositions** match doc 20 §§2–8: F7 at the tail, Phase-4 demand
  gating, the EH1 firewall in both directions, EH2 outline-only.
- **Supersession rules 1–6** are verbatim doc 08 §2.1 including the `(created_at, id)`
  tie-break and the per-target speculative gate.
- **Dedup, post-processor, rescue** match doc 06 §4–§6; the events substrate matches doc
  04 §8.1 and doc 12 §7.
- **E0's state of play matches the repo exactly** — `bench_db.py` and `caching_llm.py`
  present with their tests, `ledger`/`corpus`/`ingest`/`run_smoke` absent, six Alembic
  revisions, both gold files and the `--algo-only` flag real.
- **No dependency cycles** across all 156 edges. The one forward edge (T2.27 → T2.40) is
  the gate that opens its own lane and is sound.
- **Critical path** verified independently each round; see the round-2 section for its
  current length and shape.
- **Task arithmetic** and the tier distribution reproduce exactly from `progress.md`.

---

# Round 2 — 2026-07-25, after remediation

The remediation above was itself reviewed, by three more Fable-tier reviewers with
disjoint lenses: fidelity of the 48 tasks added or split (which had been written from
round 1's *summary* of the design docs rather than the docs themselves), verification that
each round-1 disposition was honest, and sizing plus dependency structure.

**They found 35 further findings, including two blockers and one dishonest disposition.**

## The dishonest disposition

`B-F8` was recorded as "done-when items added", and `e2e-test-plan.md` asserted *"Each spec
is named in its owning task's Done when, so the task cannot complete without it."* Neither
was true. Git showed all eight owning tasks changed only by the inserted `Size:` field, and
no spec name appeared in any epic file. **A safeguard was described in the present tense
that did not exist** — the invariant-14 failure this corpus exists to prevent, written into
the document about preventing it.

This is why `scripts/check_plan.py` now exists. Every claim the corpus makes about itself
that can be checked mechanically is checked, and the build fails otherwise. The honesty-spec
claim is now assertion #4 in that linter; it passed only after all eight specs were really
named in their owning tasks.

## What round 2 changed

| Area | Change |
|---|---|
| **Blockers** | T2.45 (`supersede()` primitive) and T3.23 (articles channel) were dead leaves nothing depended on. Wired to T2.12 and to T3.10/T3.22. |
| **Gate edges** | Round 1 claimed the gate was added to "each epic's entry tasks"; it had been added to two. E1 had no path to G-A at all. Now every task in E1/E2/E3 transitively requires its entry gate, or carries an explicit `gate-exempt` marker — enforced by the linter. |
| **A missing emitter** | `fact_lift` must emit `sources_changed` (doc 08 §5.2). Without it, the Phase-5 hook is a no-op on first ingest (doc 05 §8.4), so newly lifted facts would never be enqueued for promotion. Added to T2.10. |
| **Three inventions removed** | T1.42c demanded a test that the DNS-rebinding check cannot be disabled, when `*` is a sanctioned opt-out; T1.52/T1.54 required an F1 number over an unlabelled corpus, which is not computable; T2.43 put code search inside the four-layer composition doc 07 §2 excludes it from. |
| **A design-doc conflict surfaced** | Doc 08 §3.4's prose and its own diagram disagree on the status bridge's guard-2 behaviour. T2.45 now names the conflict and routes it as a **Tier-3 amendment** rather than silently picking the reading that retires memories still asserting live facts. |
| **Critical path** | Three edges on it were intuition, not necessity — most clearly `T1.17 → T1.23`, which forced the pure-function taxonomy to wait for the pipeline rebuild that *consumes* it. Removing them, and making gate barriers real edges, took the path from 31 (Depends-only, barrier-blind) to **29 barrier-aware**. The post-processor chain is no longer on it. |
| **Four new tasks** | T2.54 (label the gold set, split from the harvest so compute does not stall on human labelling), T2.55 (grouping / no-triple-count), T2.56 (cold start + output shapes), T2.57 (contradiction-pair gold, which T2.52 measured against and nobody built). |
| **Sizing** | ~22 re-sized in both directions against the real backend. 27 S / 145 M / 32 L. |
| **Regressions repaired** | The split commit had silently dropped a `T1.14` edge the remediation commit added one commit earlier; two tasks had been repointed from a whole contract to only its first part; runbook section references were stale after a renumbering, including one the tracker generator re-emitted. |

## What is now machine-verified

`python scripts/check_plan.py` asserts, and fails on: every task reference resolving; no
dependency cycles; every task carrying its full field set; every epic task reaching its
entry gate or declaring exemption; **every honesty spec being named in its owning task**;
every inert object naming a real writer task; no infrastructure task left as a dead leaf
without a `terminal-by-design` marker; every runbook section cross-reference resolving;
no stale task counts; and this ledger reconciling with its own header.

`gen_progress.py` and `gen_task_graph.py` derive the tracker and the graphs from the task
files, so neither can drift. **`risks-and-lanes.md` Part 1 remains hand-written** and is
therefore the corpus's last drift surface — round 2 found three stale claims there and
nowhere else.
