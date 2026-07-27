# Progress tracker

**Regenerated from the epic files** by
`scripts/gen_progress.py` — task ids, titles, model tiers, and effort are derived, never
hand-copied, so the two cannot drift. Only the state columns (Owner, Status, Commit,
Review, Note) are edited by hand.

The epic files in [`tasks/`](tasks/) are the source of truth for *scope*; this file
tracks *state*. If they disagree about what a task is, the epic file wins — and the
disagreement is an amendment to log.

## Status vocabulary

| Status | Means |
|---|---|
| `todo` | Not started. Check the epic's entry gate before claiming — an open gate
blocks the whole epic regardless of `Depends`. |
| `wip` | Claimed. The **Owner** column names who; one owner at a time. |
| `blocked` | Started and stopped. The **Note** column must say what blocks it. |
| `review` | Code complete, awaiting the Fable-tier review that Opus-tier and
gate-feeding tasks require. The **Review** column carries the reviewer's verdict. |
| `done` | Every definition-of-done item in runbook §4 holds, verification output
recorded, commit landed, and any required review passed. |

**A task is never `done` with a failing check.** If the suite is red it is `blocked`
and the Note says so. That rule is the whole point of this file.

## Claiming and concurrency

- **This file is canonical on `master`**, not on an epic branch — otherwise it forks per
  branch and no copy is true. Update it with a single commit touching only your row.
- **Claiming is one commit** setting Owner and moving the row to `wip`. If two agents
  race, the later commit loses and that agent picks another task — cheap, because the
  loser has done no work yet.
- **Review is tracked in the Review column**, not as separate rows. Every Opus-tier
  task and every task feeding a gate claim needs one before it can reach `done`.
- Regenerate the derived columns and the rollup with `python scripts/gen_progress.py`
  after any task is added, split, or retitled. It carries the five state columns
  through unchanged, so regenerating mid-execution is safe and never resets a claim.

## Rollup

| Epic | Tasks | todo | wip | blocked | review | done | Gate |
|---|---|---|---|---|---|---|---|
| E0 — Baseline & harness | 20 | 0 | 0 | 0 | 0 | 20 | **G-A CLEARED 2026-07-27** |
| E1 — Engine core | 75 | 68 | 0 | 0 | 0 | 7 | G-B open |
| E2 — Truth core | 57 | 57 | 0 | 0 | 0 | 0 | G-C, G-D open |
| E3 — Synthesis & reach | 26 | 26 | 0 | 0 | 0 | 0 | G-E open |
| E4 — Hardening & scale | 10 | 10 | 0 | 0 | 0 | 0 | demand-gated |
| EH1 — Documents / PKM | 17 | 17 | 0 | 0 | 0 | 0 | G-F open |
| EH2 — .NET migration | outline | — | — | — | — | — | G-G closed |
| **Total** | **205** | **178** | **0** | **0** | **0** | **27** | |

---

## E0 — Baseline & harness (20 tasks)

| Task | Title | Size | Model | Effort | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|---|
| T0.01 | Append-only run ledger (`benchlib/ledger.py`) | M | Sonnet | high | claude/e0-lane-a | done | 70b3ea1 | sonnet: spec compliant, approved; fable adversarial review a63675c | ledger.py + 7 tests; benchlib conftest fixture made opt-in. Verify 7 passed; floor 614 passed, 1 skipped |
| T0.02 | Corpus loader (`benchlib/corpus.py`) | S | Haiku | high | claude/e0-lane-a | done | ac05908 | sonnet: approved after 1 fix round; fable adversarial review a63675c | corpus.py + smoke/corpus.json + 11 tests; raw-membership taxonomy validation. Verify 11 passed; floor 614 passed, 1 skipped |
| T0.03 | Offline ingest driver (`benchlib/ingest.py`) | M | Sonnet | high | claude/e0-lane-a | done | f6c658f | sonnet: spec compliant, approved; fable adversarial review a63675c | ingest.py over the real ProcessingPipeline; caching_llm extended to embed_batch. Verify 8 passed; floor 614 passed, 1 skipped |
| T0.04 | `run_smoke.py` and the affordability gate | M | Sonnet | high | claude/e0-lane-a | done | ea2428b | sonnet: approved after 1 fix round; fable adversarial review a63675c | run_smoke.py + FROZEN.md; gate asserts zero live calls AND clean per-pass outcomes. Verify exit 0, `live LLM calls: 0`, 3 memories/6 entities/3 relations per pass; floor 614 passed, 1 skipped |
| T0.05 | Record the as-is extraction F1 baseline | M | Fable | high | claude/e0-lane-a | done | 684a35e | fable adversarial: addressed after 2 fix rounds | As-is F1 recorded on gold+held-out (4 dims) + G-B tolerance in gate-ledger.md. 36 live DeepSeek calls; cache archived under docs/eval/. Verify --algo-only reproduces byte-identical; floor 614 passed, 1 skipped |
| T0.06 | Retrieval gold set + query-type slices | M | Fable | high | claude/e0-lane-b | done | 61c0046 | fable adversarial: addressed after 1 fix round | 102 pairs / 7 slices over a 72-memory fixed-id corpus, + SLICES.md. Anchor flags make retire-and-replace a test failure. Verify 28 passed; benchlib 132; floor 614 passed, 1 skipped |
| T0.06a | Re-adjudicate the saturated multi-hop pairs | M | Fable | high | claude/e0-lane-b | done | 96c2ed0 | fable adversarial: spec FAIL, 2 Important; addressed after 1 fix round | Multi-hop desaturated: hit@10 0.929 -> 0.000, every live pair now a designed miss. Corpus 72 -> 94 (retrieval_limit=94), gold v4, 102 live pairs (118 authored, 16 retired). Bridges now verified present in the extracted graph, not just the text. Verify 43 passed; benchlib 175; floor 614 passed, 1 skipped |
| T0.07 | Sliced accuracy scorer (MRR / hit@K) | M | Sonnet | high | claude/e0-lane-b | done | 54a43d9 | fable adversarial: addressed after 1 fix round | Sliced MRR/hit@K + real-retriever driver. Baseline pooled MRR 0.857 / hit@10 0.971 over 102 pairs. Verify 24 passed; benchlib 160; floor 614 passed, 1 skipped |
| T0.08 | Latency and token-cost twin | M | Sonnet | high | claude/e0-lane-b | done | 2432986 | fable adversarial: spec PASS, 4 Important; addressed after 1 fix round | benchlib/twin.py: p95 per channel (live vs cache-served kept separate), tokens by purpose, usage persisted into the cache so warm runs report unknown not zero. Accuracy without a twin is unconstructible. Verify 23 passed; benchlib 198; floor 614 passed, 1 skipped; gate exit 0 |
| T0.09 | Full-context baseline comparator | M | Opus | high | claude/e0-lane-b | done | e7ab956 | fable adversarial: spec PASS, 1 Important; addressed after 1 fix round | benchlib/full_context.py: stuffs all 94 memories, scored by the SAME scorer as retrieval. Full context WINS on accuracy (pooled MRR 0.907 vs 0.858, hit@10 0.931 vs 0.843) at 472,558 prompt tokens and p95 1.54s vs cached ms. Comparability caveats derive from the twins. Verify 48 passed; benchlib 249; floor 614 passed, 1 skipped; gate exit 0 |
| T0.10 | Retrieval eval runner + dated report | M | Sonnet | high | claude/e0-lane-b | done | 4e4c1e3 | fable adversarial: spec FAIL, 2 Important; addressed after 1 fix round | run_retrieval_eval.py + docs/eval/2026-07-27-retrieval-eval.md. Two runs differ only in latency; accuracy and tokens byte-identical. Runtime guard asserts expected caveat kinds; the designed-state note fires only at hit@k==0. benchlib 276; floor 614 passed, 1 skipped |
| T0.11 | Target schema snapshot + baseline design note | L | Opus | high | claude/e0-lane-c | done | 99f2935 | —  (Fable adversarial review still owed) | baseline-schema-inventory.md: 34 tables, all 63 indexes + 59 constraints dispositioned, 8 partition templates, 10 inert objects each naming a quoted first writer, SQL-first audit. 27 findings; 2 Tier-3 escalated and both adjudicated by the maintainer. Verify: check_plan GREEN, floor 614 passed 1 skipped |
| T0.12a | Baseline part 1: core memory, graph, and taxonomy tables | M | Opus | high | claude/e0-lane-c | done | 4865858 | — | Baseline part 1 in plain SQL via op.execute; revisions 0001-0006 deleted in the same commit, one head. Floor-exempt by design |
| T0.12b | Baseline part 2: knowledge, code, jobs, and events tables | M | Opus | high | claude/e0-lane-c | done | ca0fbf0 | — | Baseline part 2: knowledge vault, memory satellites, code graph, ops, events (RANGE monthly + month-0 child). Probes: cross-project memory_relation rejected by the composite FK, dangling citation rejected by the hard FK. Floor-exempt by design |
| T0.12c | Baseline part 3: partition templates, indexes, full-suite green | L | Opus | high | claude/e0-lane-c | done | ad63a3d | — | Re-sized M->L (F-22); executed from a reviewed step-level plan. Closed all 108 read-path failures: llm_ renames, audit_log onto events, LLM indirection retired. Floor asserted: 606 passed 1 skipped 0 failed against the baseline alone; one head, one revision, one file |
| T0.13 | Dormant objects landed inert | M | Sonnet | high | claude/e0-lane-c | done | c1fe34e | — | repo_ids[] + GIN; both orphan sweeps carry the NOT EXISTS (live repo) predicate, vacuous today so the 5 graph tests pass unchanged. test_inert_objects.py asserts no writer, and one test proves the predicate SPARES a repo-asserted row while still reaping a ghost. Floor 616 passed |
| T0.14 | Boot-time partition reconciliation, idempotent | M | Opus | high | claude/e0-lane-c | done | 40e8dc0 | — | Permanent boot-time reconciliation replacing the one-time sweep; child DDL shared by register() and reconcile() so they cannot drift; child_table() the sole namer (asserted). Manual double-boot: 8 -> 8, one dropped child regrown exactly (7->8). Floor 622 passed |
| T0.15 | Freeze event + regeneration protocol | S | Haiku | high | | done | 4e44655 | — | Both protocols: the freeze EVENT (tag schema-frozen) and the during-window rule (regenerate in place, never append 0002; serialise through one owner per epic). Assertion wired into gate.sh; verified red on a deliberate 0002. Freeze date deliberately blank |
| T0.16 | Scripted merge-gate runner | M | Sonnet | high | | done | aada376 | — | scripts/gate.sh: alembic single-revision, backend pytest, frontend typecheck/test/build, benchlib, F1 --algo-only; --full adds retrieval eval + e2e. Reaps every process group it starts. Verified green, and red naming the gate on a deliberate failure |
| T0.17 | G-A evidence run and ledger entry | M | Fable | xhigh | | done | d99d470 | — | G-A CLEARED, all three probes. F1 reproduced all 8 cells byte-for-byte (0 live calls); retrieval eval MRR 0.8582/hit@10 0.8431, p95 2.43ms, full-context 472,558 prompt tokens (0 live calls, 2 caveats recorded); clean boot + idempotent reconciliation. Found and fixed the benchlib MLProfile break the floor could not see |

## E1 — Engine core (75 tasks)

| Task | Title | Size | Model | Effort | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|---|
| T1.01 | Flatten `llm_purpose_configs` to inline rows | L | Opus | high | claude/e1-engine-core | done | f7ade9f, 04ae49f | fable adversarial: spec PASS all 4 boxes, 1 Important + 4 Minor; re-review ADDRESSED (04ae49f) | Re-sized L→M. One-query resolution asserted by a statement-counting test (now matches WITH too — a CTE walked past the original). **F-10 decided: `provider` DROPPED** end-to-end. Review found a 3rd sweep miss in repo-root `scripts/ensure_ollama_models.py`: one loud break, one silent path returning [] and exiting 0. Re-keyed on `api_kind`+base-URL port, which also fixes a pre-existing miss of Ollama-compat rows; overclaimed evidence sentence corrected in the log and inventory F-10. Gate GREEN exit 0 — backend 774 passed/1 skipped, frontend 336 + typecheck + build, benchlib 276, F1 0.925/0.955/0.865/0.892 |
| T1.02 | One shared `httpx.AsyncClient` with atomic live reload | M | Sonnet | high | | todo | | | |
| T1.03 | `api_kind` as the sole vendor-quirk home | M | Opus | high | claude/e1-lane-a | wip | | | |
| T1.04 | `classifier_kind` inline on the classification purpose | M | Sonnet | high | | todo | | | |
| T1.05 | Seed `synthesis` and `verification` purposes inert | S | Haiku | high | claude/e1-engine-core | done | d61cca9 | — (Haiku tier; no Fable review required) | Both purposes seeded AND swept into `PURPOSES` + the Settings defaults map — doc 11 §6 requires the sweep before any consumer dispatches, and a purpose in `PURPOSES` with no default is a KeyError on a fresh install. Inert = nothing dispatches, not not-configured. 3 guards, each mutation-checked. First writers T2.26 / T3.02. Two tests that hard-coded the six purposes now derive from `PURPOSES`. Verify 13 passed; floor backend 777 passed/1 skipped, frontend 336 + typecheck + build |
| T1.06 | `events` table, monthly partitioning, append-only trigger | M | Opus | high | claude/e1-engine-core | done | 0168f98, 04ae49f | fable adversarial: spec PASS, 1 Important + 8 Minor; re-review ADDRESSED (04ae49f) | Three forbid-triggers, not doc 04's one; per-child TRUNCATE guard (parent's does not cascade — measured PG 17). Review found `events_ensure_partition` emitted session-timezone-dependent bounds: months created under UTC then +07 silently leave a 7-hour hole, failing journaled requests. Bounds now UTC-pinned; guard matched by OID; mid-month normalised; concurrent duplicate_table caught; arm runs first in its own session. Gate GREEN exit 0 — backend 774 passed/1 skipped, frontend 336 + typecheck + build, benchlib 276, F1 0.925/0.955/0.865/0.892 |
| T1.07 | `events` writer and the journaling convention | M | Sonnet | high | claude/e1-lane-b | done | b43eec3 | — (Sonnet tier; Fable review owed before G-B) | `record_event` generalised into the journaling convention: never raises, isolating each insert in its own SAVEPOINT so a broken journal degrades loudly without failing or poisoning the caller's transaction. Closed `EVENT_TYPES`/`OBJECT_TYPES` kept beside their writer, not in `taxonomy.py` — they are code literals, not LLM-emitted, so an unknown value warns instead of being silently rewritten. Wired capture, pipeline outcome, and supersession. **Merge-time defect found by benchlib alone** (backend was 909 green with it present): the journal read `mem_record`, bound inside savepoint A, which a failed Phase 1 skips — every memory in that batch took an UnboundLocalError instead of an outcome. Binding hoisted; outcome derivation unified in `_derive_outcome` so journal and broadcast cannot disagree. Gate GREEN exit 0 — backend 911 passed/1 skipped, frontend 336 + typecheck + build, benchlib 276, F1 0.925/0.955/0.865/0.892 |
| T1.08 | `GET /events`, `/events/calendar`, `/events/timeline` | M | Sonnet | high | claude/e1-lane-b | wip | | | |
| T1.09 | Retire `audit_log` reads | S | Sonnet | high | | todo | | | |
| T1.10 | `memory_buffer` table + pre-minted UUIDv7 ids | M | Sonnet | high | claude/e1-engine-core | done | 33b896d, 04ae49f | fable adversarial: spec PASS, 3 Important + 4 Minor; re-review ADDRESSED (04ae49f) | UUIDv7 via `uuid6` (floor raise rejected: image is python:3.12-slim). Review found the buffer id and pre-minted memory id must be **two distinct ids** (doc 05 §2.2, T1.10's own owning section, unread by me) — unwound; memory id rides `metadata_`. `REPLAYED_METADATA_FIELDS` gained the caller's `metadata`. Durability proven cross-connection. Gate GREEN exit 0 — backend 774 passed/1 skipped, frontend 336 + typecheck + build, benchlib 276, F1 0.925/0.955/0.865/0.892 |
| T1.11 | `origin_key` resolution — born at capture | M | Opus | high | claude/e1-engine-core | wip | | | |
| T1.12 | Tier-A synchronous accept + 202 ack | M | Sonnet | high | | todo | | | |
| T1.13 | `buffer_flush` job with `FOR UPDATE SKIP LOCKED` | M | Opus | high | | todo | | | |
| T1.14 | `wait_process` interactive bypass | M | Sonnet | high | | todo | | | |
| T1.15 | Repo-hint auto-provision handoff + SSRF allowlist gate | M | Opus | high | | todo | | | |
| T1.16 | Phase 1: content embed + register-before-insert | M | Opus | high | | todo | | | |
| T1.17 | Phase 2: merged extract + classify in one call | L | Opus | high | | todo | | | |
| T1.18 | `classifier_kind=local` narrowing path | S | Sonnet | high | | todo | | | |
| T1.19 | Phase 3: entity embed with the two-level cache | M | Opus | high | | todo | | | |
| T1.20 | Phase 4: type-constrained dedup + `names_distinct` | M | Opus | high | | todo | | | |
| T1.21 | Phase 5: the two-savepoint write | L | Opus | high | | todo | | | |
| T1.22 | Mid-batch embedder rotation | M | Opus | high | | todo | | | |
| T1.23 | Five closed vocabularies + normalisers + `LEGACY_*` maps | M | Opus | high | claude/e1-engine-core | done | f74ba76, 04ae49f | fable adversarial: spec PASS (1 box deferred, logged), 3 Important + 5 Minor; re-review ADDRESSED (04ae49f) | MEMORY_TYPES 7→9; memory-relation set reserved (5 stored, SUPERSEDES projected). Review found `PRECEDES→FOLLOWS` silently inverted edge direction (alias deleted), the demo fixture still carried 1000 `context` rows (regenerated), and a pre-existing invariant-5 hole on the update path (closed + pinned). **The F1-green does NOT measure the widening**: the bench cache key covers only the system prompt, while the schema string rides the user message — real measurement is G-B's live run. Gate GREEN exit 0 — backend 774 passed/1 skipped, frontend 336 + typecheck + build, benchlib 276, F1 0.925/0.955/0.865/0.892 |
| T1.24a | Pass registry, the ordering contract, and the per-pass harness | M | Opus | high | claude/e1-lane-c | done | b43eec3 | — (Opus tier; Fable review owed before G-B) | Ordered `PASS_REGISTRY` + `ORDERING_CONSTRAINTS`, validated at import so a bad reorder cannot be imported. 28 top-level entries (not doc 06's ~40 — that count includes sub-passes; logged). Pass bodies untouched: F1 unmoved AND a stricter equivalence check compared full output dicts over all cached extractions in both gold files under both `relation_rescue` states — 72 cases, 0 mismatches. All three ordering constraints mutation-checked both with the import guard and with it disabled. Found doc 06 §4's stated reason for constraint 1 wrong (dedup has no substring rule); doc corrected, constraint unchanged. Gate GREEN exit 0 — backend 911 passed/1 skipped, frontend 336 + typecheck + build, benchlib 276, F1 0.925/0.955/0.865/0.892 |
| T1.24b | Stage 1: entity shaping | M | Opus | high | claude/e1-lane-c | wip | | | |
| T1.24c | Stage 2: entity rescue | M | Opus | high | | todo | | | |
| T1.24d | Stage 4: relation gating and direction | L | Opus | high | | todo | | | |
| T1.24e | Stage 5: collapse, dedup, fan-out | L | Opus | high | | todo | | | |
| T1.24f | Whole-chain F1 parity against the recorded baseline | M | Fable | high | | todo | | | |
| T1.25 | `relation_rescue` layer | M | Opus | high | | todo | | | |
| T1.26 | Strip-before-rewrite: idempotent re-extraction | M | Opus | high | | todo | | | |
| T1.27 | `technologies` denorm recompute | M | Opus | high | | todo | | | |
| T1.28 | `graph_orphan_cleanup` backstop | S | Sonnet | high | | todo | | | |
| T1.29a | Pushdown on the semantic channel | M | Opus | high | | todo | | | |
| T1.29b | Pushdown on the keyword and graph channels | M | Opus | high | | todo | | | |
| T1.29c | Pushdown on `memory_reason` and code search | M | Opus | high | | todo | | | |
| T1.30 | RRF fusion + the unified `rank_fusion_factor` | M | Opus | high | | todo | | | |
| T1.31 | Ranking arms wired at zero | S | Sonnet | high | | todo | | | |
| T1.32 | Reranker wired dormant | S | Sonnet | high | | todo | | | |
| T1.33 | The retrieval trace | M | Sonnet | high | | todo | | | |
| T1.34 | `applies_when` context-boost slot | M | Opus | high | | todo | | | |
| T1.35 | The isolation probe (G-B's zero-count) | M | Fable | high | | todo | | | |
| T1.36 | Supersession detector, rules 1–6 verbatim | M | Opus | high | | todo | | | |
| T1.37 | TTL sweep, demote before delete | M | Opus | high | | todo | | | |
| T1.38 | T1 fail-stale | M | Sonnet | high | | todo | | | |
| T1.39 | T2 index-debt drain | M | Opus | high | | todo | | | |
| T1.40 | T3 `code_reconcile` job | M | Sonnet | high | | todo | | | |
| T1.41 | T4 summary carry-over | S | Sonnet | high | | todo | | | |
| T1.42a | Payload envelope + source and context resolution | L | Opus | high | | todo | | | |
| T1.42b | REST surface conformance | M | Sonnet | high | | todo | | | |
| T1.42c | MCP surface parity and transport hardening | M | Opus | high | | todo | | | |
| T1.42d | Two-door parity audit | S | Opus | high | | todo | | | |
| T1.43 | Dashboard + contribution calendar | M | Sonnet | high | | todo | | | |
| T1.44 | Memories search + the why-retrieved trace | M | Sonnet | high | | todo | | | |
| T1.45 | Pipeline stepper, failure triage, job board | M | Sonnet | high | | todo | | | |
| T1.46 | Code fail-stale banner + index-debt indicator | M | Sonnet | high | | todo | | | |
| T1.47 | Memory-detail supersession lineage | M | Sonnet | high | | todo | | | |
| T1.48 | Detail-level preference honoured across advanced surfaces | M | Sonnet | high | | todo | | | |
| T1.49 | WebSocket → query-invalidation mapping | M | Sonnet | high | | todo | | | |
| T1.50 | G-B evidence run and ledger entry | M | Fable | xhigh | | todo | | | |
| T1.51 | Cutover transform + carried-set column map | L | Opus | high | | todo | | | |
| T1.52 | Tier-C re-extraction backfill + verification counts | L | Opus | high | | todo | | | |
| T1.53 | Cutover rehearsal on a dump copy + restore drill | M | Sonnet | high | | todo | | | |
| T1.54 | Execute the cutover, verify, apply the freeze tag | M | Fable | high | | todo | | | |
| T1.55 | Settings → LLM: six inline purpose cards | M | Sonnet | high | | todo | | | |
| T1.56 | Setup wizard finalize against the flattened config | M | Sonnet | high | | todo | | | |
| T1.57 | Settings → Flags, bound to `config` | M | Sonnet | high | | todo | | | |
| T1.58 | Retire demo mode as the default | L | Sonnet | high | | todo | | | |
| T1.59 | Bind the Code section to live data | L | Sonnet | high | | todo | | | |
| T1.60 | Bind Chat and the Memory Graph explorer | L | Sonnet | high | | todo | | | |
| T1.61 | Activity: feed, day view, and the buffer monitor | M | Sonnet | high | | todo | | | |
| T1.62 | App-as-edge deployment artifact | L | Opus | high | | todo | | | |
| T1.63 | Bind Settings: Security, Maintenance, Jobs | M | Sonnet | high | | todo | | | |
| T1.64 | API e2e suite + the honesty specs | L | Sonnet | high | | todo | | | |
| T1.65 | `projectStore`, `contextStore`, and the project switcher | M | Sonnet | high | | todo | | | |

## E2 — Truth core (57 tasks)

| Task | Title | Size | Model | Effort | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|---|
| T2.01 | `knowledge_triples` rebuild: the bi-temporal belief axis | L | Opus | high | | todo | | | |
| T2.02 | `fact_sources` and origin-diversity counting | M | Opus | high | | todo | | | |
| T2.03 | The verification ladder | L | Opus | high | | todo | | | |
| T2.04 | The contradiction veto is absolute | M | Opus | high | | todo | | | |
| T2.05 | Human ratification is the only path to `confirmed` | S | Opus | high | | todo | | | |
| T2.06 | Every ladder transition journaled | M | Sonnet | high | | todo | | | |
| T2.07 | `projects` table + lazy registration | M | Sonnet | high | | todo | | | |
| T2.08 | Job-family umbrella under JobRegistry | M | Sonnet | high | | todo | | | |
| T2.09 | `verification_recompute` | S | Sonnet | high | | todo | | | |
| T2.10 | `fact_lift` | M | Opus | high | | todo | | | |
| T2.11 | `contradiction_scan` | M | Opus | high | | todo | | | |
| T2.12 | `memory_dream` — never hard-merges, never deletes | L | Opus | high | | todo | | | |
| T2.13 | Dream digest + per-action and per-batch undo | L | Opus | high | | todo | | | |
| T2.14 | Register `article_synthesis` inert | S | Haiku | high | | todo | | | |
| T2.15 | Five associative types + normaliser | S | Sonnet | high | | todo | | | |
| T2.16 | Derivation from overlap, proximity, and contradiction | L | Opus | high | | todo | | | |
| T2.17 | Strip-before-rewrite and endpoint self-healing | S | Sonnet | high | | todo | | | |
| T2.18 | `memory_communities` + members, Leiden per project | L | Opus | high | | todo | | | |
| T2.19 | Labelling + `report_string` off the hot path | M | Sonnet | high | | todo | | | |
| T2.20 | Browsing, report injection, pin-suggestion diff | M | Sonnet | high | | todo | | | |
| T2.21 | `memory_overview` map-reduce tool | M | Opus | high | | todo | | | |
| T2.22 | Review queue (adjudicates truth) | M | Sonnet | high | | todo | | | |
| T2.23 | Hygiene queue (curates housekeeping) + bulk actions | M | Sonnet | high | | todo | | | |
| T2.24 | Consequence ranking + dispute-staleness decay | M | Opus | high | | todo | | | |
| T2.25 | Labelled entailment gold set | M | Fable | high | | todo | | | |
| T2.26 | `verification`-purpose judge + precision/recall bars | L | Fable | high | | todo | | | |
| T2.27 | `assert_from_repo` — imports-only, LLM-free | M | Opus | high | | todo | | | |
| T2.28 | Lift to facts born `corroborated` | M | Opus | high | | todo | | | |
| T2.29 | `memory_access_stats` feeder | M | Sonnet | high | | todo | | | |
| T2.30 | `w_importance` activation | M | Fable | high | | todo | | | |
| T2.31 | `w_heat` / `w_recency` activation | M | Fable | high | | todo | | | |
| T2.32 | PPR snapshot job + graph arms | L | Opus | high | | todo | | | |
| T2.33 | `triple_embeddings` writer, miss-rate gated | M | Opus | high | | todo | | | |
| T2.34 | `expires_at` self-expiring dated facts | M | Opus | high | | todo | | | |
| T2.35 | `applies_when` magnitude tuning | M | Fable | high | | todo | | | |
| T2.36 | Facts tab — bi-temporal, multi-origin browsing | M | Sonnet | high | | todo | | | |
| T2.37 | Review / Hygiene triage shell | M | Sonnet | high | | todo | | | |
| T2.38 | Dream digest UI with undo | M | Sonnet | high | | todo | | | |
| T2.39 | Topics tab | M | Sonnet | high | | todo | | | |
| T2.40 | G-C evidence run | M | Fable | xhigh | | todo | | | |
| T2.41 | G-D evidence run | M | Fable | xhigh | | todo | | | |
| T2.42 | Facts retrieval channel, born with pushdown | M | Opus | high | | todo | | | |
| T2.43 | Four-layer composition, labelling, and grouping | L | Opus | high | | todo | | | |
| T2.44 | Arm-ablation interface for the retrieval eval | M | Sonnet | high | | todo | | | |
| T2.45 | The Tier-C `supersede()` primitive + status bridge | L | Opus | high | | todo | | | |
| T2.46 | Demotion hysteresis and the `under-sourced` label | M | Opus | high | | todo | | | |
| T2.47 | The enqueue-for-verification emit hook | M | Opus | high | | todo | | | |
| T2.48 | Citation re-verifier + code-fact lifecycle | M | Opus | high | | todo | | | |
| T2.49 | `relation_embeddings` refresh job + writer | M | Sonnet | high | | todo | | | |
| T2.50 | Graph-arm activation measurement | M | Fable | high | | todo | | | |
| T2.51 | Promotion-metrics runner | S | Sonnet | high | | todo | | | |
| T2.52 | Contradiction-shortlist miss-rate runner | M | Sonnet | high | | todo | | | |
| T2.53 | Register `topic_detection` on the schedule | S | Haiku | high | | todo | | | |
| T2.54 | Label the entailment gold set | L | Fable | high | | todo | | | |
| T2.55 | Grouping under the fact, and the no-triple-count rule | M | Opus | high | | todo | | | |
| T2.56 | Cold-start behaviour and the output shapes | M | Sonnet | high | | todo | | | |
| T2.57 | Contradiction-pair gold set | M | Fable | high | | todo | | | |

## E3 — Synthesis & reach (26 tasks)

| Task | Title | Size | Model | Effort | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|---|
| T3.01 | Subject eligibility gate + priority scoring | M | Opus | high | | todo | | | |
| T3.02 | `article_synthesis` productive runs | L | Opus | high | | todo | | | |
| T3.03 | Claim-level entailment pass + coverage routing | L | Opus | high | | todo | | | |
| T3.04 | `article_citations` — the one hard FK | S | Sonnet | high | | todo | | | |
| T3.05 | Staleness gate + debounced re-synthesis | M | Opus | high | | todo | | | |
| T3.06 | Articles tab | M | Sonnet | high | | todo | | | |
| T3.07 | Research-agent loop through the ordinary capture door | M | Opus | high | | todo | | | |
| T3.08 | Distinct-origin stamping for researched sources | M | Opus | high | | todo | | | |
| T3.09 | Managed-block writer, client-side pull-then-write | M | Opus | high | | todo | | | |
| T3.10 | Truth-first content fill under a token budget | L | Opus | high | | todo | | | |
| T3.11 | Per-tool adapters (Claude Code, Cursor, Codex, Cline) | M | Sonnet | high | | todo | | | |
| T3.12 | Inject records journaled as events | M | Sonnet | high | | todo | | | |
| T3.13 | `darkmem connect <tool>` | M | Sonnet | high | | todo | | | |
| T3.14 | Minimal TypeScript + Python SDKs | M | Sonnet | high | | todo | | | |
| T3.15 | Browser capture extension | L | Sonnet | high | | todo | | | |
| T3.16 | `session_checkpoints` table + REST/MCP surface | M | Sonnet | high | | todo | | | |
| T3.17 | Resume as a specialised inject | M | Opus | high | | todo | | | |
| T3.18 | Checkpoints are operational, not vault knowledge | S | Sonnet | high | | todo | | | |
| T3.19 | Settings → Distribution tab | M | Sonnet | high | | todo | | | |
| T3.20 | Inject records in timeline and calendar | M | Sonnet | high | | todo | | | |
| T3.21 | Session checkpoints / resume view | M | Sonnet | high | | todo | | | |
| T3.22 | G-E evidence run | M | Fable | xhigh | | todo | | | |
| T3.23 | Articles retrieval channel + `article_embeddings` writer | M | Opus | high | | todo | | | |
| T3.24 | Coverage-distribution runner | S | Sonnet | high | | todo | | | |
| T3.25 | SDK scaffold and generator | M | Sonnet | high | | todo | | | |
| T3.26 | Browser-extension scaffold | S | Sonnet | high | | todo | | | |

## E4 — Hardening & scale (10 tasks)

| Task | Title | Size | Model | Effort | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|---|
| T4.01 | Bearer credential shape + closed scope set | M | Opus | high | | todo | | | |
| T4.02 | Stamp `events.api_key_id` / `events.actor` | S | Sonnet | high | | todo | | | |
| T4.03 | Exposed-deployment posture | M | Opus | high | | todo | | | |
| T4.04 | `ApiKey` use surfaced in the per-object timeline | S | Sonnet | high | | todo | | | |
| T4.05 | Push webhook receiver | M | Sonnet | high | | todo | | | |
| T4.06 | Inject `watch` mode | M | Sonnet | high | | todo | | | |
| T4.07 | Auto-scrape opt-in | M | Sonnet | high | | todo | | | |
| T4.08 | Watch + curb surfaces on the Distribution tab | S | Sonnet | high | | todo | | | |
| T4.09 | In-process assumption audit | M | Opus | high | | todo | | | |
| T4.10 | Multi-replica decision record | M | Fable | high | | todo | | | |

## EH1 — Documents / PKM (17 tasks)

| Task | Title | Size | Model | Effort | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|---|
| TH1.01 | Faithfulness metric definition (before any build) | M | Fable | high | | todo | | | |
| TH1.02 | `documents` / `blocks` first writer | M | Opus | high | | todo | | | |
| TH1.03 | Parser stack (PDF, markdown, notes) | M | Sonnet | high | | todo | | | |
| TH1.04 | Block tree + strip-before-rewrite by `document_id` | L | Opus | high | | todo | | | |
| TH1.05 | `block_embeddings__<slug>` writer | M | Sonnet | high | | todo | | | |
| TH1.06 | Semantic-only block channel | M | Opus | high | | todo | | | |
| TH1.07 | Trace addendum: `block` id-kind, `document` layer | M | Sonnet | high | | todo | | | |
| TH1.08 | Grounded Q&A flow | L | Opus | high | | todo | | | |
| TH1.09 | Span-support faithfulness check before serving | L | Opus | high | | todo | | | |
| TH1.10 | Faithfulness ship gate (G-F evidence) | M | Fable | xhigh | | todo | | | |
| TH1.11 | On-demand Tier-C lift | M | Opus | high | | todo | | | |
| TH1.12 | Block-sourced facts, one document = one origin | M | Opus | high | | todo | | | |
| TH1.13 | Idempotent lifting, keyed on `document_id` | S | Sonnet | high | | todo | | | |
| TH1.14 | Single-document summary (unbadged) | S | Sonnet | high | | todo | | | |
| TH1.15 | Emergent cross-document connections | M | Sonnet | high | | todo | | | |
| TH1.16 | Documents UI, horizon-labelled | M | Sonnet | high | | todo | | | |
| TH1.17 | Faithfulness-gate runner | S | Sonnet | high | | todo | | | |
