import type {
  DemoBufferMonitor,
  DemoDayBucket,
  DemoDreamAction,
  DemoDreamCycle,
  DemoDreamMonitor,
  DemoFeedEvent,
  DemoPipelineFailure,
  DemoPipelineRun,
  DemoSessionRun,
} from "../types"

// ---------------------------------------------------------------------------
// S18 — pipeline runs. A partial or failed run always NAMES its failed step
// (derive_memory_failed_step vocabulary); the running row renders every node
// pending because /ws carries no per-phase progress event.
// ---------------------------------------------------------------------------

export const CURATED_PIPELINE_RUNS: DemoPipelineRun[] = [
  {
    id: "mem_7c4e19",
    content:
      '"DATABASE_URL is derived from the DB_* vars with percent-encoded credentials unless an explicit DATABASE_URL overrides it"',
    time_label: "claimed 12s ago",
    steps: ["pending", "pending", "pending", "pending", "pending"],
    substeps: null,
    terminal: "running",
    counts: null,
    note: "processing — awaiting the terminal result. All five phases resolve server-side before /ws reports one status (completed/partial/failed); there is no incremental per-phase progress event.",
  },
  {
    id: "mem_2a9f04",
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
    content:
      '"REPLACES targets are lowercased before the supersession detector compares them against memories.technologies"',
    time_label: "2026-07-24 09:03",
    steps: ["ok", "ok", "ok", "ok", "error"],
    substeps: { vector: "ok", graph: "error" },
    terminal: "partial",
    counts: { entities: 5, relations: 3 },
    note: "Vector write (savepoint A) committed independently — the memory is embedded and searchable. The entity/relationship graph write (savepoint B) failed and rolled back on its own; surfaces in Failure triage for retry.",
  },
  {
    id: "mem_9e02f7",
    content:
      '"confidence defaults to 0.75 and feeds _apply_confidence_weighting once confidence_rank_gamma is raised above zero"',
    time_label: "2026-07-24 09:07",
    steps: ["ok", "degraded", "ok", "ok", "ok"],
    substeps: { vector: "ok", graph: "ok" },
    terminal: "partial",
    counts: { entities: 1, relations: 0 },
    note: "Extraction returned a truncated response — degraded, not fatal. Content and vector are written and searchable; the entity graph carries only what parsed. A clean re-extraction resolves the row automatically.",
  },
  {
    id: "mem_e41a88",
    content:
      '"the two-tier entity-embedding cache checks the in-memory layer before the DB layer, falling back to embedding cache misses directly"',
    time_label: "2026-07-24 03:52",
    steps: ["error", "error", "skipped", "skipped", "skipped"],
    substeps: { vector: "skipped", graph: "skipped" },
    terminal: "failed",
    counts: { entities: 0, relations: 0 },
    note: "Embedder outage — the chunked embed_batch call errored, then the concurrent extraction call errored independently on the same outage. Write never ran (vector and graph both stayed skipped). Retryable from Failure triage.",
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
// S22 — staged monitors: buffer depth + dream run. live:false because the
// backing tables/jobs do not exist yet (invariant 23) — the target block is
// the sign-off design, labelled "target design · not yet live".
// ---------------------------------------------------------------------------

export const CURATED_BUFFER_MONITOR: DemoBufferMonitor = {
  live: false,
  staged_phase:
    "target-new, staged — ships once memory_buffer (doc 04 §8.6) is live",
  staged_reason:
    "Once the durable Tier-B ingest buffer ships, this panel will show live pending / claimed / done / error counts for memory_buffer, with a poison row (attempts exceeded) surfacing here and in Failure triage rather than looping forever.",
  target: {
    pending: 18,
    claimed: 4,
    done: 214,
    error: 4,
    poison: {
      headline: "1 buffer row flagged poison — attempts exceeded",
      detail:
        'project: darkmem · attempts 5/5 · last_error: "extraction timeout after 30s"',
    },
    wait_process_note:
      "wait_process=true captures bypass the buffer entirely and run the five-phase pipeline synchronously — they never appear in these counts, only in the pipeline stepper.",
  },
}

export const CURATED_DREAM_MONITOR: DemoDreamMonitor = {
  live: false,
  staged_phase:
    "target-new, staged — ships once the consolidation job family (doc 08 §5) is live",
  staged_reason:
    'Once fact_lift, verification_recompute, contradiction_scan, memory_dream, topic_detection, and article_synthesis are registered Tier-C jobs, this panel will show a live run of the dependency chain — which job is running, which are queued behind it, and the busy (409) outcome if "Dream now" lands on a lock the scheduler already holds. The per-action ledger a completed cycle leaves behind is the separate Dream digest tab.',
  target: {
    last_cycle_label:
      "last full cycle: 2026-07-23 03:00–03:04 UTC · all 6 jobs completed",
    chain: [
      { key: "fact_lift", caption: "done · cron */15 * * * *", state: "ok" },
      {
        key: "verification_recompute",
        caption: "running · cron */2 * * * *",
        state: "active",
      },
      {
        key: "contradiction_scan",
        caption: "queued · cron 0 */6 * * *",
        state: "pending",
      },
      {
        key: "memory_dream",
        caption: "queued · cron 0 3 * * *",
        state: "pending",
      },
      {
        key: "topic_detection",
        caption: "queued · daily per project",
        state: "pending",
      },
      {
        key: "article_synthesis",
        caption: "queued · daily, debounced",
        state: "pending",
      },
    ],
    narrative:
      "verification_recompute is running — draining sources_changed since 03:02:00. contradiction_scan, memory_dream, topic_detection, and article_synthesis stay queued behind it in dependency order until it finishes.",
    lock_note:
      "Each job holds its own per-job lock. A manual Dream now trigger that lands on a lock the scheduled loop already holds returns busy (HTTP 409) rather than queueing — the running job is never interrupted.",
  },
}

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
    claim: "disputed: 2 origins assert X, 1 origin asserts not-X, as of T",
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
    note: "The contradiction scan surfaced this dispute this cycle — it is not one of the seven reversible dream actions and has no undo of its own; a dispute is adjudicated, not reversed. It routes to the Review queue for a human to ratify one side or leave both served.",
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
    undone_note: "undone — restored to active, superseded_by cleared; journaled",
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
    claim:
      'before: "note about db retries" · after: "exponential backoff retry policy for transient asyncpg connection errors, max 3 attempts"',
    meta: "refined 2026-07-24 03:02 UTC",
    undone: false,
    undone_note: "undone — prior summary restored; journaled",
  },
  {
    id: "dream-ref-tags",
    type: "refine",
    cycle: 128,
    layer: 0,
    title: "tags rewritten",
    claim: "before: [db, retry] · after: [db, retry, asyncpg, backoff]",
    meta: "refined 2026-07-24 03:02 UTC",
    undone: false,
    undone_note: "undone — prior tags restored; journaled",
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
    undone_note: "undone — the 4 derived edges deleted; journaled",
  },
  {
    id: "dream-edge-reranker",
    type: "edge_derive",
    cycle: 128,
    layer: 0,
    title: '+3 associative edges · subject-salient memories on "reranker"',
    meta: "derived 2026-07-24 03:03 UTC",
    undone: false,
    undone_note: "undone — the 3 derived edges deleted; journaled",
  },
  {
    id: "dream-prom-hybrid",
    type: "promote_demote",
    cycle: 128,
    layer: 2,
    title: "hybrid_search_enabled is on by default; RRF k=60",
    claim:
      "asserted by 3 distinct origins of kinds [code, memory], no known contradiction, as of 2026-07-24",
    meta: "promoted 2026-07-24 03:02 UTC",
    transition: { from: "candidate", to: "corroborated" },
    undone: false,
    undone_note: "undone — rung restored to candidate; journaled",
  },
  {
    id: "dream-dem-gamma",
    type: "promote_demote",
    cycle: 128,
    layer: 2,
    title:
      "confidence_rank_gamma defaults to 0 — weighting is inactive until raised above zero",
    claim: "origin count dropped below N this cycle — demoted, not disputed",
    meta: "demoted 2026-07-24 03:02 UTC",
    transition: { from: "corroborated", to: "candidate" },
    caution_tag: "demoted",
    undone: false,
    undone_note: "undone — rung restored to corroborated; journaled",
  },
  {
    id: "dream-ratify-reranker",
    type: "ratify",
    cycle: 128,
    layer: 2,
    title: "the reranker LLM-scores the top 40 RRF-ranked rows after fusion",
    claim:
      "asserted by 4 distinct origins of kinds [code, human, memory], no known contradiction, as of 2026-07-24, human-ratified — ratified by q.tran, 2026-07-24",
    meta: "ratified 2026-07-24 03:04 UTC",
    transition: { from: "corroborated", to: "confirmed", to_label: "human-ratified" },
    undone: false,
    undone_note:
      "undone — the human-kind fact_source withdrawn, recompute queued; journaled",
  },
  {
    id: "dream-inv-setup-secret",
    type: "invalidate",
    cycle: 128,
    layer: 2,
    title: "the setup wizard requires SETUP_SECRET before /setup can run",
    claim:
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
    undone_note: "undone — belief window reopened (invalid_at cleared); journaled",
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
      "undone — article re-activated, superseded_by unlinked; journaled",
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
        inject_detail: [
          "3 facts injected (2 corroborated, 1 human-ratified)",
          "640 / 1200 token budget",
          "curb: none applied",
        ],
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

// ---------------------------------------------------------------------------
// S33 — session checkpoints. OPERATIONAL digests — no verification badge,
// always labelled "session digest · not verified knowledge".
// ---------------------------------------------------------------------------

const RESUME_BLOCK = `<!-- darkmem:resume:begin — project darkmem-core-backend · run cc-run-8f3a2c · saved 03:12 · ~1,850 tokens -->
## Resume — where you left off
Applied the Fable review to feature-epics.md (22 findings, committed 5492b20), then added
two new features behind docs/superpowers/specs/2026-07-25-detail-level-and-session-resume-design.md:
the Simple/Advanced detail toggle and this server-side session-resume subsystem.

### Next steps
1. Update the mockups (S03 simple state, C03 detail toggle, S33 checkpoints) and rebuild index.html
2. Initialise D:\\Repositories\\Personal\\claude-code-plugins with the README + plugin plan
3. Commit the docs + mockups

### Decisions
- detail toggle default = advanced; simple hides numbers/jargon, never honesty labels
- checkpoints = server-side (session_checkpoints table + endpoints + MCP), plugin planned separately

<!-- darkmem:resume:end -->`

export const CURATED_SESSION_RUNS: DemoSessionRun[] = [
  {
    id: "cc-run-8f3a2c",
    title: "Overnight: darkmem feature-epics review",
    origin_key: "cc-run-8f3a2c",
    project: "darkmem-core-backend",
    meta_label: "5 checkpoints · last 03:12 · ~1,850 tokens",
    latest: {
      saved_label: "saved 03:12 · ~1,850 tokens",
      summary:
        "Applied the Fable review to feature-epics.md: 22 confirmed findings landed across two passes (fact-layer retagged rebuild + target-new, T1–T4 retagged, a groundedness-judge row added to close E2's G-D gate, pointer/wording nits fixed), committed as 5492b20. Then added two new features to the list behind a design spec: the detail-level toggle and this session-resume subsystem.",
      next_steps: [
        "Update the mockups (S03 simple, C03 toggle, this screen) and rebuild index.html",
        "Initialise the plugin marketplace repo with the README + plan",
        "Commit the docs + mockups",
      ],
      key_decisions: [
        "toggle default = advanced",
        "checkpoints = server-side",
        "plugin = plan-only this pass",
      ],
      touched_files: [
        "docs/planning/feature-epics.md",
        "docs/superpowers/specs/2026-07-25-…md",
        "docs/design/mockups/fragments/*",
      ],
      resume_block: RESUME_BLOCK,
    },
    history: [
      {
        time_label: "08:41",
        event: "resumed",
        detail: "new session loaded the 03:12 digest into CLAUDE.md",
        tokens_label: "~1,850",
      },
      {
        time_label: "03:12",
        event: "checkpoint_saved",
        detail: "features added behind the spec; ready to update mockups",
        tokens_label: "~1,850",
      },
      {
        time_label: "01:48",
        event: "checkpoint_saved",
        detail: "Fable review applied + committed 5492b20",
        tokens_label: "~1,610",
      },
      {
        time_label: "00:20",
        event: "checkpoint_saved",
        detail: "review workflow returned; verdict revise",
        tokens_label: "~1,240",
      },
    ],
  },
  {
    id: "cc-run-1d77e0",
    title: "Frontend skeleton — Wave 4 build",
    origin_key: "cc-run-1d77e0",
    project: "darkmem",
    meta_label: "0 checkpoints · no digest yet",
    latest: null,
    history: [],
  },
]
