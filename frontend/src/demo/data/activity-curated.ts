import type { DemoPipelineFailure, DemoPipelineRun } from "@/features/activity/types"
import type {
  DemoDayBucket,
  DemoDreamAction,
  DemoDreamCycle,
  DemoFeedEvent,
} from "../types"

// ---------------------------------------------------------------------------
// S18 — pipeline runs. A partial or failed run always NAMES its failed step
// (derive_memory_failed_step vocabulary); the running row renders every node
// pending because /ws carries no per-phase progress event.
// ---------------------------------------------------------------------------

export const CURATED_PIPELINE_RUNS: DemoPipelineRun[] = [
  {
    id: "mem_7c4e19",
    memory_id: null,
    content:
      '"DATABASE_URL is derived from the DB_* vars with percent-encoded credentials unless an explicit DATABASE_URL overrides it"',
    time_label: "claimed 12s ago",
    steps: ["pending", "pending", "pending", "pending", "pending"],
    substeps: null,
    terminal: "running",
    counts: null,
    note: "processing",
  },
  {
    id: "mem_2a9f04",
    memory_id: null,
    content:
      '"cookie_secure is tri-state: unset means Secure only when environment=production; an explicit false allows login over plain-HTTP LAN"',
    time_label: "2026-07-23 18:41",
    steps: ["ok", "ok", "ok", "ok", "ok"],
    substeps: { vector: "ok", graph: "ok" },
    terminal: "completed",
    counts: { entities: 6, relations: 4 },
    note: null,
  },
  {
    id: "mem_5b13d0",
    memory_id: null,
    content:
      '"REPLACES targets are lowercased before the supersession detector compares them against memories.technologies"',
    time_label: "2026-07-24 09:03",
    steps: ["ok", "ok", "ok", "ok", "error"],
    substeps: { vector: "ok", graph: "error" },
    terminal: "partial",
    counts: { entities: 5, relations: 3 },
    note: "The memory is saved and searchable, but its graph write failed. Retry it from Failure triage.",
  },
  {
    id: "mem_9e02f7",
    memory_id: null,
    content:
      '"confidence defaults to 0.75 and feeds _apply_confidence_weighting once confidence_rank_gamma is raised above zero"',
    time_label: "2026-07-24 09:07",
    steps: ["ok", "degraded", "ok", "ok", "ok"],
    substeps: { vector: "ok", graph: "ok" },
    terminal: "partial",
    counts: { entities: 1, relations: 0 },
    note: "Extraction returned a truncated response. The memory is searchable; its graph holds only what was parsed.",
  },
  {
    id: "mem_e41a88",
    memory_id: null,
    content:
      '"the two-tier entity-embedding cache checks the in-memory layer before the DB layer, falling back to embedding cache misses directly"',
    time_label: "2026-07-24 03:52",
    steps: ["error", "error", "skipped", "skipped", "skipped"],
    substeps: { vector: "skipped", graph: "skipped" },
    terminal: "failed",
    counts: { entities: 0, relations: 0 },
    note: "The embedding provider was unreachable, so nothing was written. Retry it from Failure triage.",
  },
]

// ---------------------------------------------------------------------------
// S19 — the live feed (transient /ws stream while the view stays open).
// ---------------------------------------------------------------------------

export const CURATED_FEED_EVENTS: DemoFeedEvent[] = [
  {
    id: "feed-1",
    type: "memory.created",
    category: "capture",
    text: 'Captured "RRF k=60 keeps rank stable across reruns" from mcp',
    time_label: "14:52 UTC — just now",
  },
  {
    id: "feed-2",
    type: "pipeline.completed",
    category: "pipeline",
    text: "Extraction + classification finished for 4 memories",
    time_label: "14:49 UTC — 3 min ago",
  },
  {
    id: "feed-3",
    type: "fact.verified",
    category: "verification",
    text: '"hybrid_search_enabled defaults on" promoted',
    time_label: "14:44 UTC — 8 min ago",
    layer: 2,
    transition: { from: "candidate", to: "corroborated" },
  },
  {
    id: "feed-4",
    type: "fact.verified",
    category: "verification",
    text: '"reranker default enablement" — disputed: 2 origins assert the reranker is enabled by default in production, 1 origin asserts it is opt-in per profile, as of 2026-07-24',
    time_label: "14:41 UTC — 11 min ago",
    layer: 2,
    badge: "disputed",
    toast: true,
  },
  {
    id: "feed-5",
    type: "consolidation.completed",
    category: "consolidation",
    text: "Dream cycle finished — 6 memories superseded, 2 facts promoted",
    time_label: "14:15 UTC — 37 min ago",
  },
  {
    id: "feed-6",
    type: "topic.detected",
    category: "consolidation",
    text: 'New topic community detected around "reranker configuration" (7 members)',
    time_label: "13:58 UTC — 54 min ago",
  },
  {
    id: "feed-7",
    type: "repo.indexing_completed",
    category: "code",
    text: "darkmem-core-backend reindexed — HEAD unchanged, symbols enriched",
    time_label: "13:40 UTC — 1 hr ago",
  },
]

// ---------------------------------------------------------------------------
// S20 — pipeline_failures triage rows. reason is the raw error_message.
// ---------------------------------------------------------------------------

export const CURATED_PIPELINE_FAILURES: DemoPipelineFailure[] = [
  {
    id: "fail-reranker-swap",
    target_kind: "memory",
    target_label:
      'memory · "Considering swapping the reranker for a cross-encoder model once…"',
    pipeline: "memory_ingest",
    failed_step: "extraction",
    reason:
      "extraction call timed out after 30s (purpose: extraction, model: glm-4.6-flash)",
    attempts: 1,
    first_failed: "2026-07-25 08:10 UTC",
    last_attempt: "2026-07-25 08:10 UTC",
    retry_queued: false,
  },
  {
    id: "fail-zai-models",
    target_kind: "memory",
    target_label:
      'memory · "Investigating whether the z.ai /v1/models endpoint can be trusted for…"',
    pipeline: "memory_ingest",
    failed_step: "extraction",
    reason:
      "extraction call timed out after 30s (purpose: extraction, model: glm-4.6-flash)",
    attempts: 7,
    first_failed: "2026-07-19 10:03 UTC",
    last_attempt: "2026-07-25 08:15 UTC",
    retry_queued: false,
  },
  {
    id: "fail-database-url",
    target_kind: "memory",
    target_label:
      'memory · "darkmem now derives DATABASE_URL from DB_PASSWORD; SETUP_SECRET removed…"',
    pipeline: "memory_ingest",
    failed_step: "content_embedding",
    reason:
      "embedder connection refused — nomic-embed-text at 192.168.0.250:11434 (embedding purpose)",
    attempts: 2,
    first_failed: "2026-07-23 21:40 UTC",
    last_attempt: "2026-07-24 08:15 UTC",
    retry_queued: false,
  },
  {
    id: "fail-frontend-leiden",
    target_kind: "code_repo",
    target_label: "code_repo · darkmem-frontend",
    pipeline: "code_index",
    failed_step: "community_detection",
    reason: "Leiden partition step exceeded the phase budget on 41,208 edges",
    attempts: 1,
    first_failed: "2026-07-24 06:41 UTC",
    last_attempt: "2026-07-24 06:41 UTC",
    retry_queued: false,
  },
]

// ---------------------------------------------------------------------------
// S23 — dream digest: one cycle's journaled ledger, grouped by action type,
// every inverse a status/pointer/timestamp restore (never a resurrection).
// ---------------------------------------------------------------------------

export const CURATED_DREAM_CYCLE: DemoDreamCycle = {
  id: 128,
  window_label: "2026-07-24 03:00 → 03:04:12 UTC (4m 12s)",
  trigger_label: "triggered: scheduled · memory_dream cron",
  undoable_until_label: "undoable until 2026-07-31",
  retention_label: "dream_undo_retention 7d",
  summary: {
    superseded: 4,
    refined: 7,
    promoted_demoted: 5,
    promoted_split: "+3 promoted (incl. 1 ratified) / −2 demoted",
    disputed: 1,
    edges_derived: 9,
  },
  groups: [
    {
      type: "supersede",
      label: "Supersession",
      count_label: "4 memories",
      more_note: "+2 more superseded this cycle",
      batchable: true,
    },
    {
      type: "refine",
      label: "Refine",
      count_label: "7 memories",
      more_note: "+5 more refined this cycle",
      batchable: true,
    },
    {
      type: "edge_derive",
      label: "Associative-edge derivation",
      count_label: "9 edges · 3 derivation events",
      more_note: "+1 more derivation this cycle (2 edges)",
      annotation:
        "Undo here deletes the specific derived edges, not the memories they connect — associative edges self-heal (idempotent strip-before-rewrite), so this undo can never resurrect a row.",
      batchable: true,
    },
    {
      type: "promote_demote",
      label: "Fact promotion / demotion",
      count_label: "4 facts (ratification shown separately below)",
      more_note: "+2 more promoted/demoted this cycle",
      batchable: true,
    },
    {
      type: "ratify",
      label: "Ratification",
      count_label: "1 fact",
      annotation:
        "A human, not the machine, performs ratification, but it journals through the same events ledger this digest reads, so it appears here for audit and undo. Undo withdraws the human-kind fact_source and re-runs recompute — ratification is authenticated per-fact, never batched.",
      batchable: false,
    },
    {
      type: "invalidate",
      label: "Fact invalidation",
      count_label: "1 fact",
      batchable: true,
    },
    {
      type: "resynthesize",
      label: "Article re-synthesis",
      count_label: "1 article",
      annotation:
        "Undo re-activates this article row and re-points superseded_by — the new article b3f8e12 is not deleted, only unlinked as the terminal successor.",
      batchable: true,
    },
  ],
  disputed: {
    legend: "disputed: 2 origins assert X, 1 origin asserts not-X, as of T",
    sides: [
      {
        assertion: "asserts X — the reranker is enabled by default in production",
        origins: "2 origins · kinds [code, memory]",
      },
      {
        assertion:
          "asserts not-X — the reranker is opt-in per profile, disabled by default",
        origins: "1 origin · kind [human]",
      },
    ],
    note: "The contradiction scan found this dispute. Resolve it in Knowledge → Review.",
  },
}

export const CURATED_DREAM_ACTIONS: DemoDreamAction[] = [
  {
    id: "dream-sup-setup-secret",
    type: "supersede",
    cycle: 128,
    layer: 0,
    title: '"the setup wizard writes SETUP_SECRET into .env during finalize"',
    meta: "superseded_by → memory 7c1e2ab · 2026-07-24 03:01 UTC",
    transition: { from: null, to: "superseded", from_plain: "active" },
    undone: false,
    undone_note: "undone — restored to active",
  },
  {
    id: "dream-sup-mcp-bearer",
    type: "supersede",
    cycle: 128,
    layer: 0,
    title:
      '"the MCP endpoint requires SETUP_SECRET as a bearer token for /mcp calls"',
    meta: "superseded_by → memory a91f0c3 · 2026-07-24 03:01 UTC",
    transition: { from: null, to: "superseded", from_plain: "active" },
    undo_blocked: {
      reason:
        "a newer change rewrote this object. This memory was edited again 2026-07-24 04:10, outside this cycle; the before-state this undo would restore is no longer current.",
    },
    undone: false,
  },
  {
    id: "dream-ref-summary",
    type: "refine",
    cycle: 128,
    layer: 0,
    title: "summary rewritten · content unchanged (refine never touches content)",
    note:
      'before: "note about db retries" · after: "exponential backoff retry policy for transient asyncpg connection errors, max 3 attempts"',
    meta: "refined 2026-07-24 03:02 UTC",
    undone: false,
    undone_note: "undone — prior summary restored",
  },
  {
    id: "dream-ref-tags",
    type: "refine",
    cycle: 128,
    layer: 0,
    title: "tags rewritten",
    note: "before: [db, retry] · after: [db, retry, asyncpg, backoff]",
    meta: "refined 2026-07-24 03:02 UTC",
    undone: false,
    undone_note: "undone — prior tags restored",
  },
  {
    id: "dream-edge-cookie",
    type: "edge_derive",
    cycle: 128,
    layer: 0,
    title:
      '+4 associative edges · 3 co-retrieved memories on "cookie_secure" (similarity ≥ 0.85)',
    meta: "derived 2026-07-24 03:03 UTC",
    undone: false,
    undone_note: "undone — the 4 derived edges deleted",
  },
  {
    id: "dream-edge-reranker",
    type: "edge_derive",
    cycle: 128,
    layer: 0,
    title: '+3 associative edges · subject-salient memories on "reranker"',
    meta: "derived 2026-07-24 03:03 UTC",
    undone: false,
    undone_note: "undone — the 3 derived edges deleted",
  },
  {
    id: "dream-prom-hybrid",
    type: "promote_demote",
    cycle: 128,
    layer: 2,
    title: "hybrid_search_enabled is on by default; RRF k=60",
    badge_claim:
      "asserted by 3 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-24",
    meta: "promoted 2026-07-24 03:02 UTC",
    transition: { from: "candidate", to: "corroborated" },
    undone: false,
    undone_note: "undone — rung restored to candidate",
  },
  {
    id: "dream-dem-gamma",
    type: "promote_demote",
    cycle: 128,
    layer: 2,
    title:
      "confidence_rank_gamma defaults to 0 — weighting is inactive until raised above zero",
    note: "origin count dropped below N this cycle — demoted, not disputed",
    meta: "demoted 2026-07-24 03:02 UTC",
    transition: { from: "corroborated", to: "candidate" },
    caution_tag: "demoted",
    undone: false,
    undone_note: "undone — rung restored to corroborated",
  },
  {
    id: "dream-ratify-reranker",
    type: "ratify",
    cycle: 128,
    layer: 2,
    title: "the reranker LLM-scores the top 40 RRF-ranked rows after fusion",
    badge_claim:
      "asserted by 4 distinct origins of kinds [code, human, memory], no known contradiction, as of 2026-07-24, human-ratified",
    meta: "ratified 2026-07-24 03:04 UTC",
    transition: { from: "corroborated", to: "confirmed", to_label: "human-ratified" },
    undone: false,
    undone_note:
      "undone — the human confirmation withdrawn",
  },
  {
    id: "dream-inv-setup-secret",
    type: "invalidate",
    cycle: 128,
    layer: 2,
    title: "the setup wizard requires SETUP_SECRET before /setup can run",
    note:
      "every live triple asserting this closed its belief window — SETUP_SECRET was removed; no resurrection needed to undo",
    meta: "invalidated 2026-07-24 03:02 UTC",
    transition: {
      from: null,
      to: null,
      from_plain: "invalid_at: —",
      to_plain: "invalid_at: 2026-07-24 03:02 UTC",
    },
    undo_label: "Undo — reopen window",
    undone: false,
    undone_note: "undone — fact reopened",
  },
  {
    id: "dream-resynth-setup",
    type: "resynthesize",
    cycle: 128,
    layer: 3,
    title: '"Setup & first-run — from empty database to first capture"',
    meta: "superseded_by → article b3f8e12, 2026-07-24 03:03 UTC · fact_set_hash changed enough to re-trigger synthesis",
    transition: { from: null, to: "superseded", from_plain: "active" },
    undo_label: "Undo — re-activate",
    undone: false,
    undone_note:
      "undone — article restored",
  },
]

export const CURATED_DREAM_PAST_ACTIONS: DemoDreamAction[] = [
  {
    id: "dream-past-refine-119",
    type: "refine",
    cycle: 119,
    layer: 0,
    title: "summary rewritten · cycle #119",
    meta: "refined 2026-07-10 · window closed 2026-07-17",
    undo_blocked: {
      reason: "dream_undo_retention elapsed (7 days; window closed 2026-07-17)",
    },
    undone: false,
  },
  {
    id: "dream-past-sup-121",
    type: "supersede",
    cycle: 121,
    layer: 0,
    title: '"reranker top-K fixed at 20 rows" · cycle #121',
    meta: "superseded 2026-07-12 · window closed 2026-07-19",
    undo_blocked: {
      reason: "dream_undo_retention elapsed (7 days; window closed 2026-07-19)",
    },
    undone: false,
  },
]

// ---------------------------------------------------------------------------
// S24 — day drill-down: UTC day-buckets of the durable events substrate.
// ---------------------------------------------------------------------------

export const DAY_DRILL_DEFAULT = "2026-07-20"

export const CURATED_DAY_BUCKETS: DemoDayBucket[] = [
  {
    date: "2026-07-20",
    events: [
      {
        time_label: "07:58 UTC",
        type: "created",
        link_label:
          'memory 5c81e0f2 — "hybrid_search_enabled defaults on; RRF fusion runs k=60"',
        note: "captured via mcp",
      },
      {
        time_label: "07:59 UTC",
        type: "extracted",
        link_label: "memory 5c81e0f2",
        note: "3 entities / 2 relations written to the graph (pipeline Phase 2)",
      },
      {
        time_label: "09:41 UTC",
        type: "verified",
        link_label: 'fact — "hybrid_search_enabled is on by default; RRF k=60"',
        transition: {
          from: "corroborated",
          to: "confirmed",
          to_label: "human-ratified",
        },
        note: "ratified by a human reviewer — asserted by 3 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-20",
      },
      {
        time_label: "11:20 UTC",
        type: "inject",
        link_label: "distribution target: claude-code (managed block)",
        inject: {
          tool: "claude-code",
          context_file: "CLAUDE.md",
          fact_ids: [
            "0f2c1a5e-0000-4000-8000-000000000001",
            "0f2c1a5e-0000-4000-8000-000000000002",
            "0f2c1a5e-0000-4000-8000-000000000003",
          ],
          article_ids: [],
          memory_ids: [],
          budget_tokens: 1200,
          tokens_used: 640,
        },
        note: "verification status and layer survived the injection — a corroborated fact renders as corroborated inside the tool, never re-labelled",
      },
      {
        time_label: "13:47 UTC",
        type: "consolidated",
        link_label:
          'fact — "confidence_rank_gamma defaults to 0 — weighting is inactive until raised above zero"',
        note: "Tier-C consolidation cycle #142 folded 2 duplicate facts into this row",
      },
      {
        time_label: "15:05 UTC",
        type: "repo_synced",
        link_label: "repository darkmem",
        note: "HEAD advanced to a1b2c3d — 12 files changed, code graph re-indexed",
      },
      {
        time_label: "18:30 UTC",
        type: "superseded",
        link_label:
          'memory 902fbb14 — "the reranker scores every fused row, not just the top 40"',
        badge: "superseded",
        note: "superseded_by memory 33ad61c7 — the reranker cutoff doc was rewritten",
      },
    ],
  },
  {
    date: "2026-07-19",
    events: [
      {
        time_label: "10:12 UTC",
        type: "created",
        link_label:
          'memory 8842aa10 — "asyncpg needs CAST on raw-SQL params or IndeterminateDatatypeError"',
        note: "captured via api",
      },
      {
        time_label: "10:13 UTC",
        type: "extracted",
        link_label: "memory 8842aa10",
        note: "2 entities / 1 relation written to the graph (pipeline Phase 2)",
      },
    ],
  },
]
