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
| `done` | Every definition-of-done item in runbook §3 holds, verification output
recorded, commit landed, and any required review passed. |

**A task is never `done` with a failing check.** If the suite is red it is `blocked`
and the Note says so. That rule is the whole point of this file.

## Claiming and concurrency

- **This file is canonical on `main`**, not on an epic branch — otherwise it forks per
  branch and no copy is true. Update it with a single commit touching only your row.
- **Claiming is one commit** setting Owner and moving the row to `wip`. If two agents
  race, the later commit loses and that agent picks another task — cheap, because the
  loser has done no work yet.
- **Review is tracked in the Review column**, not as separate rows. Every Opus-tier
  task and every task feeding a gate claim needs one before it can reach `done`.
- Regenerate the derived columns and the rollup with `python scripts/gen_progress.py`
  after any task is added, split, or retitled.

## Rollup

| Epic | Tasks | todo | wip | blocked | review | done | Gate |
|---|---|---|---|---|---|---|---|
| E0 — Baseline & harness | 17 | 17 | 0 | 0 | 0 | 0 | G-A open |
| E1 — Engine core | 65 | 65 | 0 | 0 | 0 | 0 | G-B open |
| E2 — Truth core | 53 | 53 | 0 | 0 | 0 | 0 | G-C, G-D open |
| E3 — Synthesis & reach | 26 | 26 | 0 | 0 | 0 | 0 | G-E open |
| E4 — Hardening & scale | 10 | 10 | 0 | 0 | 0 | 0 | demand-gated |
| EH1 — Documents / PKM | 17 | 17 | 0 | 0 | 0 | 0 | G-F open |
| EH2 — .NET migration | outline | — | — | — | — | — | G-G closed |
| **Total** | **188** | **188** | **0** | **0** | **0** | **0** | |

---

## E0 — Baseline & harness (17 tasks)

| Task | Title | Model | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|
| T0.01 | Append-only run ledger (`benchlib/ledger.py`) | Sonnet | | todo | | | |
| T0.02 | Corpus loader (`benchlib/corpus.py`) | Haiku | | todo | | | |
| T0.03 | Offline ingest driver (`benchlib/ingest.py`) | Sonnet | | todo | | | |
| T0.04 | `run_smoke.py` and the affordability gate | Sonnet | | todo | | | |
| T0.05 | Record the as-is extraction F1 baseline | Fable | | todo | | | |
| T0.06 | Retrieval gold set + query-type slices | Fable | | todo | | | |
| T0.07 | Sliced accuracy scorer (MRR / hit@K) | Sonnet | | todo | | | |
| T0.08 | Latency and token-cost twin | Sonnet | | todo | | | |
| T0.09 | Full-context baseline comparator | Opus | | todo | | | |
| T0.10 | Retrieval eval runner + dated report | Sonnet | | todo | | | |
| T0.11 | Target schema snapshot + baseline design note | Opus | | todo | | | |
| T0.12 | The single baseline Alembic revision | Opus | | todo | | | |
| T0.13 | Dormant objects landed inert | Sonnet | | todo | | | |
| T0.14 | Boot-time partition reconciliation, idempotent | Opus | | todo | | | |
| T0.15 | Freeze event + regeneration protocol | Haiku | | todo | | | |
| T0.16 | Scripted merge-gate runner | Sonnet | | todo | | | |
| T0.17 | G-A evidence run and ledger entry | Fable | | todo | | | |

## E1 — Engine core (65 tasks)

| Task | Title | Model | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|
| T1.01 | Flatten `llm_purpose_configs` to inline rows | Opus | | todo | | | |
| T1.02 | One shared `httpx.AsyncClient` with atomic live reload | Sonnet | | todo | | | |
| T1.03 | `api_kind` as the sole vendor-quirk home | Opus | | todo | | | |
| T1.04 | `classifier_kind` inline on the classification purpose | Sonnet | | todo | | | |
| T1.05 | Seed `synthesis` and `verification` purposes inert | Haiku | | todo | | | |
| T1.06 | `events` table, monthly partitioning, append-only trigger | Opus | | todo | | | |
| T1.07 | `events` writer and the journaling convention | Sonnet | | todo | | | |
| T1.08 | `GET /events`, `/events/calendar`, `/events/timeline` | Sonnet | | todo | | | |
| T1.09 | Retire `audit_log` reads | Sonnet | | todo | | | |
| T1.10 | `memory_buffer` table + pre-minted UUIDv7 ids | Sonnet | | todo | | | |
| T1.11 | `origin_key` resolution — born at capture | Opus | | todo | | | |
| T1.12 | Tier-A synchronous accept + 202 ack | Sonnet | | todo | | | |
| T1.13 | `buffer_flush` job with `FOR UPDATE SKIP LOCKED` | Opus | | todo | | | |
| T1.14 | `wait_process` interactive bypass | Sonnet | | todo | | | |
| T1.15 | Repo-hint auto-provision handoff + SSRF allowlist gate | Opus | | todo | | | |
| T1.16 | Phase 1: content embed + register-before-insert | Opus | | todo | | | |
| T1.17 | Phase 2: merged extract + classify in one call | Opus | | todo | | | |
| T1.18 | `classifier_kind=local` narrowing path | Sonnet | | todo | | | |
| T1.19 | Phase 3: entity embed with the two-level cache | Opus | | todo | | | |
| T1.20 | Phase 4: type-constrained dedup + `names_distinct` | Opus | | todo | | | |
| T1.21 | Phase 5: the two-savepoint write | Opus | | todo | | | |
| T1.22 | Mid-batch embedder rotation | Opus | | todo | | | |
| T1.23 | Five closed vocabularies + normalisers + `LEGACY_*` maps | Sonnet | | todo | | | |
| T1.24 | The deterministic post-processor (~40 passes) | Opus | | todo | | | |
| T1.25 | `relation_rescue` layer | Sonnet | | todo | | | |
| T1.26 | Strip-before-rewrite: idempotent re-extraction | Opus | | todo | | | |
| T1.27 | `technologies` denorm recompute | Opus | | todo | | | |
| T1.28 | `graph_orphan_cleanup` backstop | Sonnet | | todo | | | |
| T1.29 | SQL pushdown of project / status / archived on every channel | Opus | | todo | | | |
| T1.30 | RRF fusion + the unified `rank_fusion_factor` | Opus | | todo | | | |
| T1.31 | Ranking arms wired at zero | Sonnet | | todo | | | |
| T1.32 | Reranker wired dormant | Sonnet | | todo | | | |
| T1.33 | The retrieval trace | Sonnet | | todo | | | |
| T1.34 | `applies_when` context-boost slot | Opus | | todo | | | |
| T1.35 | The isolation probe (G-B's zero-count) | Fable | | todo | | | |
| T1.36 | Supersession detector, rules 1–6 verbatim | Opus | | todo | | | |
| T1.37 | TTL sweep, demote before delete | Opus | | todo | | | |
| T1.38 | T1 fail-stale | Sonnet | | todo | | | |
| T1.39 | T2 index-debt drain | Opus | | todo | | | |
| T1.40 | T3 `code_reconcile` job | Sonnet | | todo | | | |
| T1.41 | T4 summary carry-over | Sonnet | | todo | | | |
| T1.42 | REST/MCP payload envelope and two-door parity | Opus | | todo | | | |
| T1.43 | Dashboard + contribution calendar | Sonnet | | todo | | | |
| T1.44 | Memories search + the why-retrieved trace | Sonnet | | todo | | | |
| T1.45 | Pipeline stepper, failure triage, job board | Sonnet | | todo | | | |
| T1.46 | Code fail-stale banner + index-debt indicator | Sonnet | | todo | | | |
| T1.47 | Memory-detail supersession lineage | Sonnet | | todo | | | |
| T1.48 | Detail-level preference honoured across advanced surfaces | Sonnet | | todo | | | |
| T1.49 | WebSocket → query-invalidation mapping | Sonnet | | todo | | | |
| T1.50 | G-B evidence run and ledger entry | Fable | | todo | | | |
| T1.51 | Cutover transform + carried-set column map | Opus | | todo | | | |
| T1.52 | Tier-C re-extraction backfill + verification counts | Opus | | todo | | | |
| T1.53 | Cutover rehearsal on a dump copy + restore drill | Sonnet | | todo | | | |
| T1.54 | Execute the cutover, verify, apply the freeze tag | Fable | | todo | | | |
| T1.55 | Settings → LLM: six inline purpose cards | Sonnet | | todo | | | |
| T1.56 | Setup wizard finalize against the flattened config | Sonnet | | todo | | | |
| T1.57 | Settings → Flags, bound to `config` | Sonnet | | todo | | | |
| T1.58 | Retire demo mode as the default | Sonnet | | todo | | | |
| T1.59 | Bind the Code section to live data | Sonnet | | todo | | | |
| T1.60 | Bind Chat and the Memory Graph explorer | Sonnet | | todo | | | |
| T1.61 | Activity: feed, day view, and the buffer monitor | Sonnet | | todo | | | |
| T1.62 | App-as-edge deployment artifact | Opus | | todo | | | |
| T1.63 | Bind Settings: Security, Maintenance, Jobs | Sonnet | | todo | | | |
| T1.64 | API e2e suite + the honesty specs | Sonnet | | todo | | | |
| T1.65 | `projectStore`, `contextStore`, and the project switcher | Sonnet | | todo | | | |

## E2 — Truth core (53 tasks)

| Task | Title | Model | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|
| T2.01 | `knowledge_triples` rebuild: the bi-temporal belief axis | Opus | | todo | | | |
| T2.02 | `fact_sources` and origin-diversity counting | Opus | | todo | | | |
| T2.03 | The verification ladder | Opus | | todo | | | |
| T2.04 | The contradiction veto is absolute | Opus | | todo | | | |
| T2.05 | Human ratification is the only path to `confirmed` | Opus | | todo | | | |
| T2.06 | Every ladder transition journaled | Sonnet | | todo | | | |
| T2.07 | `projects` table + lazy registration | Sonnet | | todo | | | |
| T2.08 | Job-family umbrella under JobRegistry | Sonnet | | todo | | | |
| T2.09 | `verification_recompute` | Sonnet | | todo | | | |
| T2.10 | `fact_lift` | Opus | | todo | | | |
| T2.11 | `contradiction_scan` | Opus | | todo | | | |
| T2.12 | `memory_dream` — never hard-merges, never deletes | Opus | | todo | | | |
| T2.13 | Dream digest + per-action and per-batch undo | Opus | | todo | | | |
| T2.14 | Register `article_synthesis` inert | Haiku | | todo | | | |
| T2.15 | Five associative types + normaliser | Sonnet | | todo | | | |
| T2.16 | Derivation from overlap, proximity, and contradiction | Opus | | todo | | | |
| T2.17 | Strip-before-rewrite and endpoint self-healing | Sonnet | | todo | | | |
| T2.18 | `memory_communities` + members, Leiden per project | Opus | | todo | | | |
| T2.19 | Labelling + `report_string` off the hot path | Sonnet | | todo | | | |
| T2.20 | Browsing, report injection, pin-suggestion diff | Sonnet | | todo | | | |
| T2.21 | `memory_overview` map-reduce tool | Opus | | todo | | | |
| T2.22 | Review queue (adjudicates truth) | Sonnet | | todo | | | |
| T2.23 | Hygiene queue (curates housekeeping) + bulk actions | Sonnet | | todo | | | |
| T2.24 | Consequence ranking + dispute-staleness decay | Opus | | todo | | | |
| T2.25 | Labelled entailment gold set | Fable | | todo | | | |
| T2.26 | `verification`-purpose judge + precision/recall bars | Fable | | todo | | | |
| T2.27 | `assert_from_repo` — imports-only, LLM-free | Opus | | todo | | | |
| T2.28 | Lift to facts born `corroborated` | Opus | | todo | | | |
| T2.29 | `memory_access_stats` feeder | Sonnet | | todo | | | |
| T2.30 | `w_importance` activation | Fable | | todo | | | |
| T2.31 | `w_heat` / `w_recency` activation | Fable | | todo | | | |
| T2.32 | PPR snapshot job + graph arms | Opus | | todo | | | |
| T2.33 | `triple_embeddings` writer, miss-rate gated | Opus | | todo | | | |
| T2.34 | `expires_at` self-expiring dated facts | Sonnet | | todo | | | |
| T2.35 | `applies_when` magnitude tuning | Sonnet | | todo | | | |
| T2.36 | Facts tab — bi-temporal, multi-origin browsing | Sonnet | | todo | | | |
| T2.37 | Review / Hygiene triage shell | Sonnet | | todo | | | |
| T2.38 | Dream digest UI with undo | Sonnet | | todo | | | |
| T2.39 | Topics tab | Sonnet | | todo | | | |
| T2.40 | G-C evidence run | Fable | | todo | | | |
| T2.41 | G-D evidence run | Fable | | todo | | | |
| T2.42 | Facts retrieval channel, born with pushdown | Opus | | todo | | | |
| T2.43 | Four-layer composition, labelling, and grouping | Opus | | todo | | | |
| T2.44 | Arm-ablation interface for the retrieval eval | Sonnet | | todo | | | |
| T2.45 | The Tier-C `supersede()` primitive + status bridge | Opus | | todo | | | |
| T2.46 | Demotion hysteresis and the `under-sourced` label | Opus | | todo | | | |
| T2.47 | The enqueue-for-verification emit hook | Opus | | todo | | | |
| T2.48 | Citation re-verifier + code-fact lifecycle | Opus | | todo | | | |
| T2.49 | `relation_embeddings` refresh job + writer | Sonnet | | todo | | | |
| T2.50 | Graph-arm activation measurement | Fable | | todo | | | |
| T2.51 | Promotion-metrics runner | Sonnet | | todo | | | |
| T2.52 | Contradiction-shortlist miss-rate runner | Sonnet | | todo | | | |
| T2.53 | Register `topic_detection` on the schedule | Haiku | | todo | | | |

## E3 — Synthesis & reach (26 tasks)

| Task | Title | Model | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|
| T3.01 | Subject eligibility gate + priority scoring | Opus | | todo | | | |
| T3.02 | `article_synthesis` productive runs | Opus | | todo | | | |
| T3.03 | Claim-level entailment pass + coverage routing | Opus | | todo | | | |
| T3.04 | `article_citations` — the one hard FK | Sonnet | | todo | | | |
| T3.05 | Staleness gate + debounced re-synthesis | Opus | | todo | | | |
| T3.06 | Articles tab | Sonnet | | todo | | | |
| T3.07 | Research-agent loop through the ordinary capture door | Opus | | todo | | | |
| T3.08 | Distinct-origin stamping for researched sources | Opus | | todo | | | |
| T3.09 | Managed-block writer, client-side pull-then-write | Opus | | todo | | | |
| T3.10 | Truth-first content fill under a token budget | Opus | | todo | | | |
| T3.11 | Per-tool adapters (Claude Code, Cursor, Codex, Cline) | Sonnet | | todo | | | |
| T3.12 | Inject records journaled as events | Sonnet | | todo | | | |
| T3.13 | `darkmem connect <tool>` | Sonnet | | todo | | | |
| T3.14 | Minimal TypeScript + Python SDKs | Sonnet | | todo | | | |
| T3.15 | Browser capture extension | Sonnet | | todo | | | |
| T3.16 | `session_checkpoints` table + REST/MCP surface | Sonnet | | todo | | | |
| T3.17 | Resume as a specialised inject | Opus | | todo | | | |
| T3.18 | Checkpoints are operational, not vault knowledge | Sonnet | | todo | | | |
| T3.19 | Settings → Distribution tab | Sonnet | | todo | | | |
| T3.20 | Inject records in timeline and calendar | Sonnet | | todo | | | |
| T3.21 | Session checkpoints / resume view | Sonnet | | todo | | | |
| T3.22 | G-E evidence run | Fable | | todo | | | |
| T3.23 | Articles retrieval channel + `article_embeddings` writer | Opus | | todo | | | |
| T3.24 | Coverage-distribution runner | Sonnet | | todo | | | |
| T3.25 | SDK scaffold and generator | Sonnet | | todo | | | |
| T3.26 | Browser-extension scaffold | Sonnet | | todo | | | |

## E4 — Hardening & scale (10 tasks)

| Task | Title | Model | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|
| T4.01 | Bearer credential shape + closed scope set | Opus | | todo | | | |
| T4.02 | Stamp `events.api_key_id` / `events.actor` | Sonnet | | todo | | | |
| T4.03 | Exposed-deployment posture | Opus | | todo | | | |
| T4.04 | `ApiKey` use surfaced in the per-object timeline | Sonnet | | todo | | | |
| T4.05 | Push webhook receiver | Sonnet | | todo | | | |
| T4.06 | Inject `watch` mode | Sonnet | | todo | | | |
| T4.07 | Auto-scrape opt-in | Sonnet | | todo | | | |
| T4.08 | Watch + curb surfaces on the Distribution tab | Sonnet | | todo | | | |
| T4.09 | In-process assumption audit | Opus | | todo | | | |
| T4.10 | Multi-replica decision record | Fable | | todo | | | |

## EH1 — Documents / PKM (17 tasks)

| Task | Title | Model | Owner | Status | Commit | Review | Note |
|---|---|---|---|---|---|---|---|
| TH1.01 | Faithfulness metric definition (before any build) | Fable | | todo | | | |
| TH1.02 | `documents` / `blocks` first writer | Opus | | todo | | | |
| TH1.03 | Parser stack (PDF, markdown, notes) | Sonnet | | todo | | | |
| TH1.04 | Block tree + strip-before-rewrite by `document_id` | Opus | | todo | | | |
| TH1.05 | `block_embeddings__<slug>` writer | Sonnet | | todo | | | |
| TH1.06 | Semantic-only block channel | Opus | | todo | | | |
| TH1.07 | Trace addendum: `block` id-kind, `document` layer | Sonnet | | todo | | | |
| TH1.08 | Grounded Q&A flow | Opus | | todo | | | |
| TH1.09 | Span-support faithfulness check before serving | Opus | | todo | | | |
| TH1.10 | Faithfulness ship gate (G-F evidence) | Fable | | todo | | | |
| TH1.11 | On-demand Tier-C lift | Opus | | todo | | | |
| TH1.12 | Block-sourced facts, one document = one origin | Opus | | todo | | | |
| TH1.13 | Idempotent lifting, keyed on `document_id` | Sonnet | | todo | | | |
| TH1.14 | Single-document summary (unbadged) | Sonnet | | todo | | | |
| TH1.15 | Emergent cross-document connections | Sonnet | | todo | | | |
| TH1.16 | Documents UI, horizon-labelled | Sonnet | | todo | | | |
| TH1.17 | Faithfulness-gate runner | Sonnet | | todo | | | |
