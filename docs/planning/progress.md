# Progress tracker

**156 tasks across six executable epics.** The epic files in [`tasks/`](tasks/) are the
source of truth for *scope*; this file tracks *state* only. If the two disagree about what
a task is, the epic file wins — and the disagreement is an amendment to log.

## Status vocabulary

| Status | Means |
|---|---|
| `todo` | Not started. Dependencies may or may not be met — check the epic file. |
| `wip` | An agent is working it. One owner at a time. |
| `blocked` | Started and stopped. The **Note** column must say what blocks it. |
| `review` | Code complete, awaiting the Fable-tier review that Opus-tier and gate-feeding tasks require. |
| `done` | Every definition-of-done item in the runbook §3 holds, verification output recorded, commit landed. |

**A task is never `done` with a failing check.** If the suite is red, it is `blocked` and
the Note says so. That rule is the whole point of this file.

## Rollup

| Epic | Tasks | todo | wip | blocked | review | done | Gate |
|---|---|---|---|---|---|---|---|
| E0 — Baseline & harness | 17 | 17 | 0 | 0 | 0 | 0 | G-A open |
| E1 — Engine core | 50 | 50 | 0 | 0 | 0 | 0 | G-B open |
| E2 — Truth core | 41 | 41 | 0 | 0 | 0 | 0 | G-C, G-D open |
| E3 — Synthesis & reach | 22 | 22 | 0 | 0 | 0 | 0 | G-E open |
| E4 — Hardening & scale | 10 | 10 | 0 | 0 | 0 | 0 | demand-gated |
| EH1 — Documents / PKM | 16 | 16 | 0 | 0 | 0 | 0 | G-F open |
| EH2 — .NET migration | outline | — | — | — | — | — | G-G closed |
| **Total** | **156** | **156** | **0** | **0** | **0** | **0** | |

---

## E0 — Baseline & harness

| Task | Title | Model | Status | Commit | Note |
|---|---|---|---|---|---|
| T0.01 | Append-only run ledger | Sonnet | todo | | |
| T0.02 | Corpus loader | Haiku | todo | | |
| T0.03 | Offline ingest driver | Sonnet | todo | | |
| T0.04 | `run_smoke.py` + affordability gate | Sonnet | todo | | |
| T0.05 | Record as-is extraction F1 baseline | Fable | todo | | Produces the G-B tolerance |
| T0.06 | Retrieval gold set + slices | Fable | todo | | |
| T0.07 | Sliced accuracy scorer | Sonnet | todo | | |
| T0.08 | Latency + token-cost twin | Sonnet | todo | | |
| T0.09 | Full-context baseline comparator | Opus | todo | | |
| T0.10 | Retrieval eval runner + report | Sonnet | todo | | |
| T0.11 | Schema snapshot + baseline design | Opus | todo | | |
| T0.12 | Single baseline Alembic revision | Opus | todo | | Blocks most of E1 |
| T0.13 | Dormant objects landed inert | Sonnet | todo | | |
| T0.14 | Boot-time reconciliation, idempotent | Opus | todo | | |
| T0.15 | Freeze event + regeneration protocol | Haiku | todo | | |
| T0.16 | Scripted merge-gate runner | Sonnet | todo | | |
| T0.17 | **G-A evidence run** | Fable | todo | | |

## E1 — Engine core

| Task | Title | Model | Status | Commit | Note |
|---|---|---|---|---|---|
| T1.01 | Flatten `llm_purpose_configs` | Opus | todo | | |
| T1.02 | Shared `httpx.AsyncClient` + reload | Sonnet | todo | | |
| T1.03 | `api_kind` sole vendor-quirk home | Opus | todo | | |
| T1.04 | `classifier_kind` inline | Sonnet | todo | | |
| T1.05 | Seed synthesis/verification inert | Haiku | todo | | |
| T1.06 | `events` table + append-only trigger | Opus | todo | | |
| T1.07 | `events` writer + convention | Sonnet | todo | | |
| T1.08 | `/events`, `/calendar`, `/timeline` | Sonnet | todo | | |
| T1.09 | Retire `audit_log` reads | Sonnet | todo | | |
| T1.10 | `memory_buffer` + UUIDv7 pre-mint | Sonnet | todo | | |
| T1.11 | `origin_key` born at capture | Opus | todo | | Every E2 count depends on this |
| T1.12 | Tier-A accept + 202 ack | Sonnet | todo | | |
| T1.13 | `buffer_flush` SKIP LOCKED | Opus | todo | | |
| T1.14 | `wait_process` bypass | Sonnet | todo | | |
| T1.15 | Repo-hint handoff + SSRF gate | Opus | todo | | |
| T1.16 | Phase 1 embed + register-first | Sonnet | todo | | |
| T1.17 | Phase 2 merged extract+classify | Opus | todo | | |
| T1.18 | `classifier_kind=local` path | Sonnet | todo | | |
| T1.19 | Phase 3 entity embed + cache | Sonnet | todo | | |
| T1.20 | Phase 4 dedup + `names_distinct` | Opus | todo | | |
| T1.21 | Phase 5 two-savepoint write | Opus | todo | | |
| T1.22 | Mid-batch embedder rotation | Opus | todo | | |
| T1.23 | Closed vocabularies + normalisers | Sonnet | todo | | |
| T1.24 | Deterministic post-processor | Opus | todo | | The extraction moat |
| T1.25 | `relation_rescue` layer | Sonnet | todo | | |
| T1.26 | Strip-before-rewrite idempotence | Opus | todo | | |
| T1.27 | `technologies` denorm recompute | Sonnet | todo | | |
| T1.28 | `graph_orphan_cleanup` backstop | Sonnet | todo | | |
| T1.29 | **SQL pushdown on every channel** | Opus | todo | | G-B blocking prerequisite |
| T1.30 | RRF + `rank_fusion_factor` | Opus | todo | | |
| T1.31 | Ranking arms wired at zero | Sonnet | todo | | |
| T1.32 | Reranker wired dormant | Sonnet | todo | | |
| T1.33 | Retrieval trace | Sonnet | todo | | Closes the score-drop defect |
| T1.34 | `applies_when` boost slot | Opus | todo | | |
| T1.35 | Isolation probe | Fable | todo | | |
| T1.36 | Supersession rules 1–6 | Opus | todo | | |
| T1.37 | TTL sweep, demote-before-delete | Opus | todo | | |
| T1.38 | T1 fail-stale | Sonnet | todo | | |
| T1.39 | T2 index-debt drain | Opus | todo | | |
| T1.40 | T3 `code_reconcile` | Sonnet | todo | | |
| T1.41 | T4 summary carry-over | Sonnet | todo | | |
| T1.42 | REST/MCP envelope + door parity | Opus | todo | | |
| T1.43 | Dashboard + contribution calendar | Sonnet | todo | | |
| T1.44 | Memories search + why-retrieved | Sonnet | todo | | |
| T1.45 | Stepper, triage, job board | Sonnet | todo | | |
| T1.46 | Fail-stale banner + debt indicator | Sonnet | todo | | |
| T1.47 | Supersession lineage UI | Sonnet | todo | | |
| T1.48 | Detail-level across surfaces | Sonnet | todo | | Partly built in the skeleton |
| T1.49 | WebSocket → invalidation | Sonnet | todo | | |
| T1.50 | **G-B evidence run** | Fable | todo | | |

## E2 — Truth core

| Task | Title | Model | Status | Commit | Note |
|---|---|---|---|---|---|
| T2.01 | `knowledge_triples` bi-temporal rebuild | Opus | todo | | |
| T2.02 | `fact_sources` + origin diversity | Opus | todo | | Distinct origins, never rows |
| T2.03 | Verification ladder | Opus | todo | | |
| T2.04 | Contradiction veto (absolute) | Opus | todo | | |
| T2.05 | Human-only `confirmed` | Sonnet | todo | | |
| T2.06 | Ladder transitions journaled | Sonnet | todo | | G-C is computed from this |
| T2.07 | `projects` registry | Sonnet | todo | | |
| T2.08 | Job-family umbrella | Sonnet | todo | | |
| T2.09 | `verification_recompute` | Sonnet | todo | | |
| T2.10 | `fact_lift` | Opus | todo | | |
| T2.11 | `contradiction_scan` | Opus | todo | | Its miss rate gates T2.33 |
| T2.12 | `memory_dream` (no hard merge) | Opus | todo | | |
| T2.13 | Dream digest + undo | Opus | todo | | |
| T2.14 | Register `article_synthesis` inert | Haiku | todo | | |
| T2.15 | Five associative types | Sonnet | todo | | |
| T2.16 | Relation derivation | Opus | todo | | |
| T2.17 | Relation strip + self-heal | Sonnet | todo | | |
| T2.18 | Leiden communities per project | Opus | todo | | Never pin membership |
| T2.19 | Labels + report off hot path | Sonnet | todo | | |
| T2.20 | Browsing, injection, pin diff | Sonnet | todo | | |
| T2.21 | `memory_overview` map-reduce | Opus | todo | | |
| T2.22 | Review queue | Sonnet | todo | | |
| T2.23 | Hygiene queue + bulk actions | Sonnet | todo | | |
| T2.24 | Consequence ranking + decay | Opus | todo | | |
| T2.25 | Entailment gold set | Fable | todo | | Build before the judge |
| T2.26 | `verification` judge qualification | Fable | todo | | |
| T2.27 | `assert_from_repo` deriver | Opus | todo | | After G-C only |
| T2.28 | Lift born `corroborated` | Opus | todo | | One repo = one origin |
| T2.29 | `memory_access_stats` feeder | Sonnet | todo | | |
| T2.30 | `w_importance` activation | Fable | todo | | Measured or stays at zero |
| T2.31 | `w_heat` / `w_recency` activation | Fable | todo | | Measured or stays at zero |
| T2.32 | PPR snapshot + graph arms | Opus | todo | | Binds invariant 13 |
| T2.33 | `triple_embeddings` writer | Opus | todo | | Only if miss rate exceeds bar |
| T2.34 | Self-expiring dated facts | Sonnet | todo | | |
| T2.35 | `applies_when` magnitude tuning | Sonnet | todo | | |
| T2.36 | Facts tab | Sonnet | todo | | |
| T2.37 | Review / Hygiene shell | Sonnet | todo | | |
| T2.38 | Dream digest UI | Sonnet | todo | | |
| T2.39 | Topics tab | Sonnet | todo | | |
| T2.40 | **G-C evidence run** | Fable | todo | | Opens the deriver lane |
| T2.41 | **G-D evidence run** | Fable | todo | | Opens E3 |

## E3 — Synthesis & reach

| Task | Title | Model | Status | Commit | Note |
|---|---|---|---|---|---|
| T3.01 | Eligibility gate + priority score | Opus | todo | | |
| T3.02 | `article_synthesis` productive runs | Opus | todo | | |
| T3.03 | Claim entailment + coverage routing | Opus | todo | | |
| T3.04 | `article_citations` hard FK | Sonnet | todo | | |
| T3.05 | Staleness gate + debounce | Opus | todo | | |
| T3.06 | Articles tab | Sonnet | todo | | |
| T3.07 | Research loop through capture door | Opus | todo | | Tail of the phase, not earlier |
| T3.08 | Distinct-origin stamping | Opus | todo | | |
| T3.09 | Managed-block writer | Opus | todo | | Server never writes client FS |
| T3.10 | Truth-first fill under budget | Opus | todo | | |
| T3.11 | Per-tool adapters | Sonnet | todo | | |
| T3.12 | Inject records journaled | Sonnet | todo | | |
| T3.13 | `darkmem connect <tool>` | Sonnet | todo | | |
| T3.14 | TS + Python SDKs | Sonnet | todo | | No ratify verb |
| T3.15 | Browser capture extension | Sonnet | todo | | Human-triggered only in v1 |
| T3.16 | `session_checkpoints` + surface | Sonnet | todo | | Phase-1-capable if pulled |
| T3.17 | Resume as specialised inject | Opus | todo | | |
| T3.18 | Checkpoints are not vault knowledge | Sonnet | todo | | |
| T3.19 | Distribution settings tab | Sonnet | todo | | |
| T3.20 | Inject records in timeline | Sonnet | todo | | |
| T3.21 | Checkpoints / resume view | Sonnet | todo | | |
| T3.22 | **G-E evidence run** | Fable | todo | | |

## E4 — Hardening & scale (demand-gated)

| Task | Title | Model | Status | Commit | Note |
|---|---|---|---|---|---|
| T4.01 | Bearer shape + closed scopes | Opus | todo | | Trigger: real exposure |
| T4.02 | Stamp `events.api_key_id`/`actor` | Sonnet | todo | | |
| T4.03 | Exposed-deployment posture | Opus | todo | | |
| T4.04 | Key use in per-object timeline | Sonnet | todo | | |
| T4.05 | Push webhook receiver | Sonnet | todo | | Needs T4.01 |
| T4.06 | Inject `watch` mode | Sonnet | todo | | |
| T4.07 | Auto-scrape opt-in | Sonnet | todo | | |
| T4.08 | Watch + curb surfaces | Sonnet | todo | | |
| T4.09 | In-process assumption audit | Opus | todo | | |
| T4.10 | Multi-replica decision record | Fable | todo | | Never a deployment side effect |

## EH1 — Documents / PKM (horizon)

| Task | Title | Model | Status | Commit | Note |
|---|---|---|---|---|---|
| TH1.01 | Faithfulness metric definition | Fable | todo | | **Before** any build |
| TH1.02 | `documents`/`blocks` first writer | Opus | todo | | |
| TH1.03 | Parser stack | Sonnet | todo | | ADR decided, do not re-open |
| TH1.04 | Block tree + strip-before-rewrite | Opus | todo | | |
| TH1.05 | `block_embeddings` writer | Sonnet | todo | | |
| TH1.06 | Semantic-only block channel | Opus | todo | | Never fused |
| TH1.07 | Trace addendum | Sonnet | todo | | |
| TH1.08 | Grounded Q&A flow | Opus | todo | | |
| TH1.09 | Span-support check before serving | Opus | todo | | |
| TH1.10 | **G-F faithfulness ship gate** | Fable | todo | | |
| TH1.11 | On-demand Tier-C lift | Opus | todo | | Never automatic on ingest |
| TH1.12 | One document = one origin | Opus | todo | | |
| TH1.13 | Idempotent lifting | Sonnet | todo | | |
| TH1.14 | Single-document summary | Sonnet | todo | | Unbadged, never a claim |
| TH1.15 | Emergent connections | Sonnet | todo | | No new analysis engine |
| TH1.16 | Documents UI | Sonnet | todo | | |
