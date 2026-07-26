# Progress tracker

**Regenerated from the epic files** by
`scripts/gen_progress.py` — task ids, titles, and model tiers are derived, never
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
| E0 — Baseline & harness | 19 | 15 | 4 | 0 | 0 | 0 | G-A open |
| E1 — Engine core | 75 | 75 | 0 | 0 | 0 | 0 | G-B open |
| E2 — Truth core | 57 | 57 | 0 | 0 | 0 | 0 | G-C, G-D open |
| E3 — Synthesis & reach | 26 | 26 | 0 | 0 | 0 | 0 | G-E open |
| E4 — Hardening & scale | 10 | 10 | 0 | 0 | 0 | 0 | demand-gated |
| EH1 — Documents / PKM | 17 | 17 | 0 | 0 | 0 | 0 | G-F open |
| EH2 — .NET migration | outline | — | — | — | — | — | G-G closed |
| **Total** | **204** | **200** | **4** | **0** | **0** | **0** | |

---

## E0 — Baseline & harness (19 tasks)

| Task | Title | Size | Model | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|
| T0.01 | Append-only run ledger (`benchlib/ledger.py`) | M | Sonnet | claude/e0-lane-a | wip | | | |
| T0.02 | Corpus loader (`benchlib/corpus.py`) | S | Haiku | claude/e0-lane-a | wip | | | |
| T0.03 | Offline ingest driver (`benchlib/ingest.py`) | M | Sonnet | claude/e0-lane-a | wip | | | |
| T0.04 | `run_smoke.py` and the affordability gate | M | Sonnet | claude/e0-lane-a | wip | | | |
| T0.05 | Record the as-is extraction F1 baseline | M | Fable | | todo | | | |
| T0.06 | Retrieval gold set + query-type slices | M | Fable | | todo | | | |
| T0.07 | Sliced accuracy scorer (MRR / hit@K) | M | Sonnet | | todo | | | |
| T0.08 | Latency and token-cost twin | M | Sonnet | | todo | | | |
| T0.09 | Full-context baseline comparator | M | Opus | | todo | | | |
| T0.10 | Retrieval eval runner + dated report | M | Sonnet | | todo | | | |
| T0.11 | Target schema snapshot + baseline design note | L | Opus | | todo | | | |
| T0.12a | Baseline part 1: core memory, graph, and taxonomy tables | M | Opus | | todo | | | |
| T0.12b | Baseline part 2: knowledge, code, jobs, and events tables | M | Opus | | todo | | | |
| T0.12c | Baseline part 3: partition templates, indexes, full-suite green | M | Opus | | todo | | | |
| T0.13 | Dormant objects landed inert | M | Sonnet | | todo | | | |
| T0.14 | Boot-time partition reconciliation, idempotent | M | Opus | | todo | | | |
| T0.15 | Freeze event + regeneration protocol | S | Haiku | | todo | | | |
| T0.16 | Scripted merge-gate runner | M | Sonnet | | todo | | | |
| T0.17 | G-A evidence run and ledger entry | M | Fable | | todo | | | |

## E1 — Engine core (75 tasks)

| Task | Title | Size | Model | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|
| T1.01 | Flatten `llm_purpose_configs` to inline rows | L | Opus | | todo | | | |
| T1.02 | One shared `httpx.AsyncClient` with atomic live reload | M | Sonnet | | todo | | | |
| T1.03 | `api_kind` as the sole vendor-quirk home | M | Opus | | todo | | | |
| T1.04 | `classifier_kind` inline on the classification purpose | M | Sonnet | | todo | | | |
| T1.05 | Seed `synthesis` and `verification` purposes inert | S | Haiku | | todo | | | |
| T1.06 | `events` table, monthly partitioning, append-only trigger | M | Opus | | todo | | | |
| T1.07 | `events` writer and the journaling convention | M | Sonnet | | todo | | | |
| T1.08 | `GET /events`, `/events/calendar`, `/events/timeline` | M | Sonnet | | todo | | | |
| T1.09 | Retire `audit_log` reads | S | Sonnet | | todo | | | |
| T1.10 | `memory_buffer` table + pre-minted UUIDv7 ids | M | Sonnet | | todo | | | |
| T1.11 | `origin_key` resolution — born at capture | M | Opus | | todo | | | |
| T1.12 | Tier-A synchronous accept + 202 ack | M | Sonnet | | todo | | | |
| T1.13 | `buffer_flush` job with `FOR UPDATE SKIP LOCKED` | M | Opus | | todo | | | |
| T1.14 | `wait_process` interactive bypass | M | Sonnet | | todo | | | |
| T1.15 | Repo-hint auto-provision handoff + SSRF allowlist gate | M | Opus | | todo | | | |
| T1.16 | Phase 1: content embed + register-before-insert | M | Opus | | todo | | | |
| T1.17 | Phase 2: merged extract + classify in one call | L | Opus | | todo | | | |
| T1.18 | `classifier_kind=local` narrowing path | S | Sonnet | | todo | | | |
| T1.19 | Phase 3: entity embed with the two-level cache | M | Opus | | todo | | | |
| T1.20 | Phase 4: type-constrained dedup + `names_distinct` | M | Opus | | todo | | | |
| T1.21 | Phase 5: the two-savepoint write | L | Opus | | todo | | | |
| T1.22 | Mid-batch embedder rotation | M | Opus | | todo | | | |
| T1.23 | Five closed vocabularies + normalisers + `LEGACY_*` maps | M | Opus | | todo | | | |
| T1.24a | Pass registry, the ordering contract, and the per-pass harness | M | Opus | | todo | | | |
| T1.24b | Stage 1: entity shaping | M | Opus | | todo | | | |
| T1.24c | Stage 2: entity rescue | M | Opus | | todo | | | |
| T1.24d | Stage 4: relation gating and direction | L | Opus | | todo | | | |
| T1.24e | Stage 5: collapse, dedup, fan-out | L | Opus | | todo | | | |
| T1.24f | Whole-chain F1 parity against the recorded baseline | M | Fable | | todo | | | |
| T1.25 | `relation_rescue` layer | M | Opus | | todo | | | |
| T1.26 | Strip-before-rewrite: idempotent re-extraction | M | Opus | | todo | | | |
| T1.27 | `technologies` denorm recompute | M | Opus | | todo | | | |
| T1.28 | `graph_orphan_cleanup` backstop | S | Sonnet | | todo | | | |
| T1.29a | Pushdown on the semantic channel | M | Opus | | todo | | | |
| T1.29b | Pushdown on the keyword and graph channels | M | Opus | | todo | | | |
| T1.29c | Pushdown on `memory_reason` and code search | M | Opus | | todo | | | |
| T1.30 | RRF fusion + the unified `rank_fusion_factor` | M | Opus | | todo | | | |
| T1.31 | Ranking arms wired at zero | S | Sonnet | | todo | | | |
| T1.32 | Reranker wired dormant | S | Sonnet | | todo | | | |
| T1.33 | The retrieval trace | M | Sonnet | | todo | | | |
| T1.34 | `applies_when` context-boost slot | M | Opus | | todo | | | |
| T1.35 | The isolation probe (G-B's zero-count) | M | Fable | | todo | | | |
| T1.36 | Supersession detector, rules 1–6 verbatim | M | Opus | | todo | | | |
| T1.37 | TTL sweep, demote before delete | M | Opus | | todo | | | |
| T1.38 | T1 fail-stale | M | Sonnet | | todo | | | |
| T1.39 | T2 index-debt drain | M | Opus | | todo | | | |
| T1.40 | T3 `code_reconcile` job | M | Sonnet | | todo | | | |
| T1.41 | T4 summary carry-over | S | Sonnet | | todo | | | |
| T1.42a | Payload envelope + source and context resolution | L | Opus | | todo | | | |
| T1.42b | REST surface conformance | M | Sonnet | | todo | | | |
| T1.42c | MCP surface parity and transport hardening | M | Opus | | todo | | | |
| T1.42d | Two-door parity audit | S | Opus | | todo | | | |
| T1.43 | Dashboard + contribution calendar | M | Sonnet | | todo | | | |
| T1.44 | Memories search + the why-retrieved trace | M | Sonnet | | todo | | | |
| T1.45 | Pipeline stepper, failure triage, job board | M | Sonnet | | todo | | | |
| T1.46 | Code fail-stale banner + index-debt indicator | M | Sonnet | | todo | | | |
| T1.47 | Memory-detail supersession lineage | M | Sonnet | | todo | | | |
| T1.48 | Detail-level preference honoured across advanced surfaces | M | Sonnet | | todo | | | |
| T1.49 | WebSocket → query-invalidation mapping | M | Sonnet | | todo | | | |
| T1.50 | G-B evidence run and ledger entry | M | Fable | | todo | | | |
| T1.51 | Cutover transform + carried-set column map | L | Opus | | todo | | | |
| T1.52 | Tier-C re-extraction backfill + verification counts | L | Opus | | todo | | | |
| T1.53 | Cutover rehearsal on a dump copy + restore drill | M | Sonnet | | todo | | | |
| T1.54 | Execute the cutover, verify, apply the freeze tag | M | Fable | | todo | | | |
| T1.55 | Settings → LLM: six inline purpose cards | M | Sonnet | | todo | | | |
| T1.56 | Setup wizard finalize against the flattened config | M | Sonnet | | todo | | | |
| T1.57 | Settings → Flags, bound to `config` | M | Sonnet | | todo | | | |
| T1.58 | Retire demo mode as the default | L | Sonnet | | todo | | | |
| T1.59 | Bind the Code section to live data | L | Sonnet | | todo | | | |
| T1.60 | Bind Chat and the Memory Graph explorer | L | Sonnet | | todo | | | |
| T1.61 | Activity: feed, day view, and the buffer monitor | M | Sonnet | | todo | | | |
| T1.62 | App-as-edge deployment artifact | L | Opus | | todo | | | |
| T1.63 | Bind Settings: Security, Maintenance, Jobs | M | Sonnet | | todo | | | |
| T1.64 | API e2e suite + the honesty specs | L | Sonnet | | todo | | | |
| T1.65 | `projectStore`, `contextStore`, and the project switcher | M | Sonnet | | todo | | | |

## E2 — Truth core (57 tasks)

| Task | Title | Size | Model | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|
| T2.01 | `knowledge_triples` rebuild: the bi-temporal belief axis | L | Opus | | todo | | | |
| T2.02 | `fact_sources` and origin-diversity counting | M | Opus | | todo | | | |
| T2.03 | The verification ladder | L | Opus | | todo | | | |
| T2.04 | The contradiction veto is absolute | M | Opus | | todo | | | |
| T2.05 | Human ratification is the only path to `confirmed` | S | Opus | | todo | | | |
| T2.06 | Every ladder transition journaled | M | Sonnet | | todo | | | |
| T2.07 | `projects` table + lazy registration | M | Sonnet | | todo | | | |
| T2.08 | Job-family umbrella under JobRegistry | M | Sonnet | | todo | | | |
| T2.09 | `verification_recompute` | S | Sonnet | | todo | | | |
| T2.10 | `fact_lift` | M | Opus | | todo | | | |
| T2.11 | `contradiction_scan` | M | Opus | | todo | | | |
| T2.12 | `memory_dream` — never hard-merges, never deletes | L | Opus | | todo | | | |
| T2.13 | Dream digest + per-action and per-batch undo | L | Opus | | todo | | | |
| T2.14 | Register `article_synthesis` inert | S | Haiku | | todo | | | |
| T2.15 | Five associative types + normaliser | S | Sonnet | | todo | | | |
| T2.16 | Derivation from overlap, proximity, and contradiction | L | Opus | | todo | | | |
| T2.17 | Strip-before-rewrite and endpoint self-healing | S | Sonnet | | todo | | | |
| T2.18 | `memory_communities` + members, Leiden per project | L | Opus | | todo | | | |
| T2.19 | Labelling + `report_string` off the hot path | M | Sonnet | | todo | | | |
| T2.20 | Browsing, report injection, pin-suggestion diff | M | Sonnet | | todo | | | |
| T2.21 | `memory_overview` map-reduce tool | M | Opus | | todo | | | |
| T2.22 | Review queue (adjudicates truth) | M | Sonnet | | todo | | | |
| T2.23 | Hygiene queue (curates housekeeping) + bulk actions | M | Sonnet | | todo | | | |
| T2.24 | Consequence ranking + dispute-staleness decay | M | Opus | | todo | | | |
| T2.25 | Labelled entailment gold set | M | Fable | | todo | | | |
| T2.26 | `verification`-purpose judge + precision/recall bars | L | Fable | | todo | | | |
| T2.27 | `assert_from_repo` — imports-only, LLM-free | M | Opus | | todo | | | |
| T2.28 | Lift to facts born `corroborated` | M | Opus | | todo | | | |
| T2.29 | `memory_access_stats` feeder | M | Sonnet | | todo | | | |
| T2.30 | `w_importance` activation | M | Fable | | todo | | | |
| T2.31 | `w_heat` / `w_recency` activation | M | Fable | | todo | | | |
| T2.32 | PPR snapshot job + graph arms | L | Opus | | todo | | | |
| T2.33 | `triple_embeddings` writer, miss-rate gated | M | Opus | | todo | | | |
| T2.34 | `expires_at` self-expiring dated facts | M | Opus | | todo | | | |
| T2.35 | `applies_when` magnitude tuning | M | Fable | | todo | | | |
| T2.36 | Facts tab — bi-temporal, multi-origin browsing | M | Sonnet | | todo | | | |
| T2.37 | Review / Hygiene triage shell | M | Sonnet | | todo | | | |
| T2.38 | Dream digest UI with undo | M | Sonnet | | todo | | | |
| T2.39 | Topics tab | M | Sonnet | | todo | | | |
| T2.40 | G-C evidence run | M | Fable | | todo | | | |
| T2.41 | G-D evidence run | M | Fable | | todo | | | |
| T2.42 | Facts retrieval channel, born with pushdown | M | Opus | | todo | | | |
| T2.43 | Four-layer composition, labelling, and grouping | L | Opus | | todo | | | |
| T2.44 | Arm-ablation interface for the retrieval eval | M | Sonnet | | todo | | | |
| T2.45 | The Tier-C `supersede()` primitive + status bridge | L | Opus | | todo | | | |
| T2.46 | Demotion hysteresis and the `under-sourced` label | M | Opus | | todo | | | |
| T2.47 | The enqueue-for-verification emit hook | M | Opus | | todo | | | |
| T2.48 | Citation re-verifier + code-fact lifecycle | M | Opus | | todo | | | |
| T2.49 | `relation_embeddings` refresh job + writer | M | Sonnet | | todo | | | |
| T2.50 | Graph-arm activation measurement | M | Fable | | todo | | | |
| T2.51 | Promotion-metrics runner | S | Sonnet | | todo | | | |
| T2.52 | Contradiction-shortlist miss-rate runner | M | Sonnet | | todo | | | |
| T2.53 | Register `topic_detection` on the schedule | S | Haiku | | todo | | | |
| T2.54 | Label the entailment gold set | L | Fable | | todo | | | |
| T2.55 | Grouping under the fact, and the no-triple-count rule | M | Opus | | todo | | | |
| T2.56 | Cold-start behaviour and the output shapes | M | Sonnet | | todo | | | |
| T2.57 | Contradiction-pair gold set | M | Fable | | todo | | | |

## E3 — Synthesis & reach (26 tasks)

| Task | Title | Size | Model | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|
| T3.01 | Subject eligibility gate + priority scoring | M | Opus | | todo | | | |
| T3.02 | `article_synthesis` productive runs | L | Opus | | todo | | | |
| T3.03 | Claim-level entailment pass + coverage routing | L | Opus | | todo | | | |
| T3.04 | `article_citations` — the one hard FK | S | Sonnet | | todo | | | |
| T3.05 | Staleness gate + debounced re-synthesis | M | Opus | | todo | | | |
| T3.06 | Articles tab | M | Sonnet | | todo | | | |
| T3.07 | Research-agent loop through the ordinary capture door | M | Opus | | todo | | | |
| T3.08 | Distinct-origin stamping for researched sources | M | Opus | | todo | | | |
| T3.09 | Managed-block writer, client-side pull-then-write | M | Opus | | todo | | | |
| T3.10 | Truth-first content fill under a token budget | L | Opus | | todo | | | |
| T3.11 | Per-tool adapters (Claude Code, Cursor, Codex, Cline) | M | Sonnet | | todo | | | |
| T3.12 | Inject records journaled as events | M | Sonnet | | todo | | | |
| T3.13 | `darkmem connect <tool>` | M | Sonnet | | todo | | | |
| T3.14 | Minimal TypeScript + Python SDKs | M | Sonnet | | todo | | | |
| T3.15 | Browser capture extension | L | Sonnet | | todo | | | |
| T3.16 | `session_checkpoints` table + REST/MCP surface | M | Sonnet | | todo | | | |
| T3.17 | Resume as a specialised inject | M | Opus | | todo | | | |
| T3.18 | Checkpoints are operational, not vault knowledge | S | Sonnet | | todo | | | |
| T3.19 | Settings → Distribution tab | M | Sonnet | | todo | | | |
| T3.20 | Inject records in timeline and calendar | M | Sonnet | | todo | | | |
| T3.21 | Session checkpoints / resume view | M | Sonnet | | todo | | | |
| T3.22 | G-E evidence run | M | Fable | | todo | | | |
| T3.23 | Articles retrieval channel + `article_embeddings` writer | M | Opus | | todo | | | |
| T3.24 | Coverage-distribution runner | S | Sonnet | | todo | | | |
| T3.25 | SDK scaffold and generator | M | Sonnet | | todo | | | |
| T3.26 | Browser-extension scaffold | S | Sonnet | | todo | | | |

## E4 — Hardening & scale (10 tasks)

| Task | Title | Size | Model | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|
| T4.01 | Bearer credential shape + closed scope set | M | Opus | | todo | | | |
| T4.02 | Stamp `events.api_key_id` / `events.actor` | S | Sonnet | | todo | | | |
| T4.03 | Exposed-deployment posture | M | Opus | | todo | | | |
| T4.04 | `ApiKey` use surfaced in the per-object timeline | S | Sonnet | | todo | | | |
| T4.05 | Push webhook receiver | M | Sonnet | | todo | | | |
| T4.06 | Inject `watch` mode | M | Sonnet | | todo | | | |
| T4.07 | Auto-scrape opt-in | M | Sonnet | | todo | | | |
| T4.08 | Watch + curb surfaces on the Distribution tab | S | Sonnet | | todo | | | |
| T4.09 | In-process assumption audit | M | Opus | | todo | | | |
| T4.10 | Multi-replica decision record | M | Fable | | todo | | | |

## EH1 — Documents / PKM (17 tasks)

| Task | Title | Size | Model | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|---|
| TH1.01 | Faithfulness metric definition (before any build) | M | Fable | | todo | | | |
| TH1.02 | `documents` / `blocks` first writer | M | Opus | | todo | | | |
| TH1.03 | Parser stack (PDF, markdown, notes) | M | Sonnet | | todo | | | |
| TH1.04 | Block tree + strip-before-rewrite by `document_id` | L | Opus | | todo | | | |
| TH1.05 | `block_embeddings__<slug>` writer | M | Sonnet | | todo | | | |
| TH1.06 | Semantic-only block channel | M | Opus | | todo | | | |
| TH1.07 | Trace addendum: `block` id-kind, `document` layer | M | Sonnet | | todo | | | |
| TH1.08 | Grounded Q&A flow | L | Opus | | todo | | | |
| TH1.09 | Span-support faithfulness check before serving | L | Opus | | todo | | | |
| TH1.10 | Faithfulness ship gate (G-F evidence) | M | Fable | | todo | | | |
| TH1.11 | On-demand Tier-C lift | M | Opus | | todo | | | |
| TH1.12 | Block-sourced facts, one document = one origin | M | Opus | | todo | | | |
| TH1.13 | Idempotent lifting, keyed on `document_id` | S | Sonnet | | todo | | | |
| TH1.14 | Single-document summary (unbadged) | S | Sonnet | | todo | | | |
| TH1.15 | Emergent cross-document connections | M | Sonnet | | todo | | | |
| TH1.16 | Documents UI, horizon-labelled | M | Sonnet | | todo | | | |
| TH1.17 | Faithfulness-gate runner | S | Sonnet | | todo | | | |
