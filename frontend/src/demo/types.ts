import type { Repo } from "@/hooks/api"
import type { KnowledgeLayer, VerificationStatus } from "@/components/darkmem"
import type { ActivityEvent, DashboardStats } from "@/features/dashboard/types"
import type { ContributionDay } from "@/features/dashboard/types"
import type { DemoCodeGraph } from "@/features/code/types"
import type { DemoMemory } from "@/features/memories/types"
import type {
  DemoJob,
  DemoPipelineFailure,
  DemoPipelineRun,
  FeedCategory,
  JobTriggerResult,
} from "@/features/activity/types"
import type {
  DemoBehavioralFlag,
  DemoCodeBucket,
  DemoCorroborationGate,
  DemoGraphFlag,
  DemoLLMPurpose,
  DemoLLMSaveTrace,
  DemoRankArm,
  DemoTunable,
  LLMPurposeName,
  MaintenanceOpKey,
} from "@/features/settings/types"

export interface MemoryTraceChannel {
  name: string
  /** 0–1 bar fraction; null = the channel did not score this row. */
  fraction: number | null
  display?: string
}

export interface MemoryTrace {
  channels: MemoryTraceChannel[]
  rrf_score: number
  /** Plain-language "why it ranked" line for Simple mode. */
  summary: string
}

export interface MemoryExclusion {
  count: number
  unit?: string
  reason: string
  tag: string
}

export interface MemorySearchQuery {
  query: string
  /** "all" or a project name — the isolation scope, not the context. */
  project: string
  /** Session applies_when declaration, or null when not declared. */
  context: string | null
}

export interface MemorySearchOutcome {
  results: { memory: DemoMemory; trace: MemoryTrace }[]
  exclusions: MemoryExclusion[]
  /** Matches before the result cap (for "N of M shown"). */
  totalMatches: number
}

// ---------------------------------------------------------------------------
// Knowledge vault (Wave 2) — facts, articles, topics, review + hygiene queues
// ---------------------------------------------------------------------------

export type OriginKind = "memory" | "code" | "block" | "human"

export interface FactSource {
  origin_key: string
  kind: OriginKind
  ref: string
  detail: string
  /** Display timestamp line, e.g. "captured 2026-06-01 09:00". */
  at: string
  /** Doc 10 §6 (T2.48/T2.86): true when the live door's origin group this row
   *  came from is stale — a code citation the re-verifier could no longer
   *  resolve. Absent in every demo fixture, which has no re-verifier; the
   *  live adapter broadcasts the group's `stale` onto each of its rows. */
  stale?: boolean
}

export interface BeliefWindow {
  valid_at: string
  invalid_at: string | null
  expired_at: string | null
  note: string
}

export interface FactLadderEvent {
  at: string
  description: string
  /** Rung transition; `from: null` renders "candidate (no prior rung)". */
  transition?: { from: string | null; to: string }
  note?: string
}

export interface AppliesWhen {
  key: string
  value: string
  /** Who declared it — "human" or "LLM-guessed, not human-checked". */
  tag: string
}

export interface DisputeSide {
  object_name: string
  assertion: string
  origin_count: number
  origin_kinds: OriginKind[]
  sources: FactSource[]
  window: BeliefWindow
  applies_when: AppliesWhen[]
}

export interface FactDispute {
  /** The fixed two-sided claim string, filled — rendered verbatim. */
  summary: string
  sides: [DisputeSide, DisputeSide]
}

export interface CodeProvenance {
  commit_sha: string
  basis: string
  file_path: string
  symbol_key: string
}

export interface DemoFact {
  id: string
  project: string
  subject_name: string
  rel_type: string
  object_name: string
  fact_text: string
  /** Rendered verbatim — never softened or recomputed client-side. */
  verification_status: VerificationStatus
  /** The verbatim honest badge claim string. */
  claim: string
  /** Right-side meta line for the list row, e.g. "asserted by 3 distinct origins". */
  meta: string
  review_state: "open" | null
  as_of: string
  sources: FactSource[]
  windows: BeliefWindow[]
  ladder: FactLadderEvent[]
  /** Empty array = explicit "no context restriction". */
  applies_when: AppliesWhen[]
  dispute?: FactDispute
  candidate_note?: string
  under_sourced_note?: string
  code_provenance?: CodeProvenance
  ratified?: { by: string; on: string }
}

export interface ArticleCitation {
  /** Inline marker, e.g. "F1". */
  key: string
  fact_id: string
  claim_span: string
  quote: string
}

export interface ArticleSentence {
  text: string
  /** Citation key grounding this sentence, or null for connective text. */
  cite: string | null
}

export interface ArticleSection {
  label: string
  sentences: ArticleSentence[]
}

export interface DemoArticle {
  id: string
  project: string
  subject_key: string
  subject_kind: string
  title: string
  excerpt: string
  /** "superseded" REPLACES the rung badge entirely (terminal state). */
  verification_status: VerificationStatus
  claim: string | null
  review_state: "open" | null
  /** ratio === entailed / total — labelled claim-support coverage, never a vague score. */
  coverage: { ratio: number; entailed: number; total: number }
  coverage_note?: string
  /** Labelled, never hidden: set when fact_set_hash no longer matches. */
  stale: { since: string; reason: string } | null
  fact_set_hash: string
  current_fact_set_hash: string
  synthesized_at: string
  /** Right-side meta line, e.g. "ratified 2026-07-10". */
  meta: string
  applies_when_label: string
  sections: ArticleSection[]
  citations: ArticleCitation[]
  supersedes: string | null
  superseded_by: string | null
  last_rung_note?: string
  ungrounded_note?: string
}

export interface DemoCommunity {
  id: string
  label: string
  member_count: number
  impact: "high" | "medium" | "low"
  dominant_entities: string[]
  report: string | null
  report_pending: string | null
  note: string | null
}

export interface DemoPinSuggestion {
  id: string
  subject: string
  reason: string
  reason_kind: "new" | "grown"
  /** Keys on the stable dominant-entity label — community ids churn per run. */
  supporting_community: string
  member_count: number
  anchored_fact_count: number
  decision: "accepted" | "dismissed" | null
}

export interface ReviewDisputeSideSummary {
  assertion: string
  origins: string
}

export interface DemoReviewItem {
  id: string
  kind: "fact" | "article"
  target_id: string
  layer: KnowledgeLayer
  title: string
  state_tag: string
  claim_line?: string
  badge?: VerificationStatus
  under_sourced?: boolean
  coverage_pct?: number
  note?: string
  rank_note: string
  dispute_sides?: [ReviewDisputeSideSummary, ReviewDisputeSideSummary]
  decayed: boolean
  decayed_note?: string
  reground_queued?: boolean
}

export interface HygieneRow {
  id: string
  text: string
  why?: string
  meta: string
}

export interface HygieneDupPair {
  id: string
  connector: string
  rows: [HygieneRow, HygieneRow]
}

export interface HygieneLineageLink {
  text: string
  status: "superseded" | "active"
  meta: string
  why?: string
}

export interface HygieneLineageChain {
  id: string
  connector: string
  links: HygieneLineageLink[]
}

export interface HygieneQueueState {
  duplicates: HygieneDupPair[]
  lowConfidence: HygieneRow[]
  expiring: HygieneRow[]
  lineage: HygieneLineageChain[]
}

export type HygieneCategory = keyof HygieneQueueState

// ---------------------------------------------------------------------------
// Explore (Wave 3) — code repos/graph/wiki, memory graph, chat
// ---------------------------------------------------------------------------

export type DemoRepoStatus =
  | "ready"
  | "indexing"
  | "stale"
  | "error"
  | "registered"

export type IndexPhaseState = "done" | "current" | "pending" | "skipped"

export interface DemoIndexPhase {
  n: number
  label: string
  state: IndexPhaseState
}

export interface DemoWikiSection {
  id: string
  label: string
  paragraphs: string[]
  bullets?: { code: string; text: string }[]
}

export interface DemoWiki {
  generated_at: string
  /** The commit the prose describes — may lag the repo HEAD. */
  head: string
  symbol_enrichment: "complete" | "draining"
  module_summaries: "complete" | "draining"
  sections: DemoWikiSection[]
}

export interface DemoRepo {
  id: string
  name: string
  branch: string
  head: string | null
  status: DemoRepoStatus
  last_indexed_at: string | null
  index_on_commit_enabled: boolean
  /** T2 index-debt: dependent-file re-trace overflow queued past the cap,
   *  persisted and drained via continuation batches — never dropped. */
  debt: { queued_files: number; note: string } | null
  auto_provisioned: { on: string; from_memory: string } | null
  /** T1 fail-stale: the last-good graph stays served, marked stale. */
  stale: { last_good_head: string; last_good_at: string; cause: string } | null
  error: { headline: string; detail: string; message: string } | null
  /** Live phase ticker, present while status === "indexing". */
  phases: DemoIndexPhase[] | null
  /** Registered-but-never-indexed note (auto-provision Tier C queue). */
  registered_note: string | null
  wiki: DemoWiki | null
  /** Tracked source paths, POSIX-separated — the Explorer's tree. Empty
   *  for a repo that has never been indexed: there is no file listing to
   *  browse until a run has walked the tree. */
  files: string[]
}

export type MemoryEntityType = "tool" | "database" | "concept" | "algorithm"

export interface DemoMemoryEntity {
  id: string
  name: string
  entity_type: MemoryEntityType
  topic: string
  project: string
}

export interface DemoMemoryRelation {
  source: string
  target: string
  rel_type: string
}

export interface DemoMemoryTopic {
  id: string
  label: string
  detected: string
  /** Non-caution chart members only — never --chart-4 (the caution slot). */
  chart: 1 | 2 | 3 | 5
  project: string
}

export interface DemoMemoryGraph {
  entities: DemoMemoryEntity[]
  relations: DemoMemoryRelation[]
  topics: DemoMemoryTopic[]
}

export interface ChatContextRow {
  id: string
  layer: KnowledgeLayer
  /** null = the row carries no rung badge (L0 lifecycle, not the ladder). */
  verification: VerificationStatus | null
  /** What the row is about — a fact's plain-English statement (L2/L3) or a
   *  quoted memory's content (L0). NOT the badge; renamed from `claim`
   *  (T2.75 fix round 2026-08-04a, F4) because it never was one and the
   *  shared name kept `frontend/src/demo/badge-grammar.ts` from walking
   *  `claim` fields generically without false-failing on every row here. */
  subject_text: string
  /** The verbatim honest badge line (or the badge:null explanation). */
  badge_line: string
  channel?: string
  trace?: MemoryTrace
}

export interface DemoTurnContext {
  rows: ChatContextRow[]
  exclusions: MemoryExclusion[]
  /** Caution-banner copy when one retrieval channel failed this turn. */
  degraded: string | null
  /** e.g. "3 sources used this turn — see context panel". */
  sources_line: string
}

export interface DemoChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  bullets?: string[]
  context?: DemoTurnContext
}

export interface DemoChatThread {
  id: string
  title: string
  updated_label: string
  messages: DemoChatMessage[]
}

export interface ReindexOptions {
  full: boolean
  enrich_symbols: boolean
  generate_wiki: boolean
}

// ---------------------------------------------------------------------------
// Activity (Wave 4) — pipeline stepper, feed, triage, jobs, staged monitors,
// dream digest, day drill, session checkpoints
// ---------------------------------------------------------------------------

/** derive_memory_failed_step's durable named-step vocabulary. Phases 3–4
 *  (entity embed, dedup) degrade batch-wide instead of failing one memory,
 *  so they never appear here. */
export type PipelineFailedStep =
  | "content_embedding"
  | "extraction"
  | "extraction_partial"
  | "vector_write"
  | "graph_write"

export interface DemoFeedEvent {
  id: string
  /** Wire event name, e.g. "memory.created", "pipeline.completed". */
  type: string
  category: FeedCategory
  text: string
  time_label: string
  layer?: KnowledgeLayer
  transition?: { from: VerificationStatus; to: VerificationStatus }
  badge?: VerificationStatus
  /** The one event whose toast carries honesty content (fact.verified dispute). */
  toast?: boolean
}

/** One `memory_buffer` row as the monitor renders it. `attempts` is a
 *  claim count, not a failure count — it increments when a row is claimed,
 *  so it means "times claimed", never "times failed" (T1.13, T1.61
 *  ruling 1). */
export interface DemoBufferRow {
  id: string
  project: string
  attempts: number
  maxAttempts: number
  lastError: string | null
  claimedAt?: string
}

export interface DemoBufferMonitor {
  /** false — no REST surface reads memory_buffer yet, even though the
   *  table and the buffer_flush job are live (invariant 23; T1.61 ruling). */
  live: false
  staged_phase: string
  staged_reason: string
  target: {
    pending: number
    claimed: number
    done: number
    error: number
    /** Still `status='claimed'` but past `buffer_claim_visibility_seconds`
     *  — the `stale_claims()` read helper's subject. Self-healing (the
     *  `buffer_flush` job's reclaim arm resolves these automatically), so
     *  this list is observational only, never actionable. */
    staleClaims: DemoBufferRow[]
    /** `status='error'` — attempts exhausted, retained for triage forever
     *  (the retention sweep only ever deletes `done`). Actionable: retry
     *  re-queues to pending, forget deletes permanently. */
    poisonRows: DemoBufferRow[]
    wait_process_note: string
  }
}

export interface DemoDreamChainJob {
  key: string
  caption: string
  state: "ok" | "active" | "pending"
}

export interface DemoDreamMonitor {
  live: false
  staged_phase: string
  staged_reason: string
  target: {
    last_cycle_label: string
    chain: DemoDreamChainJob[]
    narrative: string
    lock_note: string
  }
}

export type DreamActionType =
  | "supersede"
  | "refine"
  | "edge_derive"
  | "promote_demote"
  | "ratify"
  | "invalidate"
  | "resynthesize"

export interface DreamTransition {
  /** Rung side of the pair; null renders the plain pill instead. */
  from: VerificationStatus | null
  to: VerificationStatus | null
  from_plain?: string
  to_plain?: string
  /** Visible label override for the `to` badge (e.g. "human-ratified"). */
  to_label?: string
}

export interface DemoDreamAction {
  id: string
  type: DreamActionType
  cycle: number
  layer: KnowledgeLayer
  title: string
  meta: string
  /**
   * Narrative subtitle for a dream action that is NOT a verification-ladder
   * transition — refine's before/after, a demotion's reason, invalidation's
   * closure sentence — prose describing the event, never a badge string.
   * Named `note`, not `claim` (T2.75 fix round 2026-08-04a, F4): it used to
   * share the `claim` key with the real badge below, which is also the key
   * `knowledge-curated.ts`'s facts and articles use for their genuine
   * badges, so a generic walk over every `claim` field would have had to
   * either false-fail on this narrative prose or skip this file. Renaming
   * it frees `claim` to mean exactly one thing everywhere it appears.
   */
  note?: string
  /** The real badge `fact_badge.build_claim` would render for this row after
   *  the transition — set only on `promote_demote` (promotion) and `ratify`
   *  actions. Walked by `badge-grammar.ts`; `note` above is not. */
  badge_claim?: string
  /** Amber per-row emphasis (demoted rung / touched a disputed object). */
  caution_tag?: string
  transition?: DreamTransition
  /** Custom verb, e.g. "Undo — reopen window". Default "Undo". */
  undo_label?: string
  /** Present ⇒ undo renders disabled WITH this reason — never hidden. */
  undo_blocked?: { reason: string }
  undone: boolean
  undone_note?: string
}

export interface DemoDreamGroup {
  type: DreamActionType
  label: string
  count_label: string
  more_note?: string
  annotation?: string
  /** Ratification is authenticated per-fact — never batched. */
  batchable: boolean
}

export interface DemoDreamCycle {
  id: number
  window_label: string
  trigger_label: string
  undoable_until_label: string
  retention_label: string
  summary: {
    superseded: number
    refined: number
    promoted_demoted: number
    promoted_split: string
    disputed: number
    edges_derived: number
  }
  groups: DemoDreamGroup[]
  disputed: {
    /** A verbatim quote of `build_claim`'s own doc-comment example
     *  ("disputed: 2 origins assert X, 1 origin asserts not-X, as of T"),
     *  teaching the shape rather than instantiating it for this cycle's
     *  actual dispute (`sides` below carries that). Named `legend`, not
     *  `claim`, so `badge-grammar.ts`'s walk does not mistake a doc
     *  placeholder for a real claim (T2.75 fix round 2026-08-04a, F4). */
    legend: string
    sides: [
      { assertion: string; origins: string },
      { assertion: string; origins: string },
    ]
    note: string
  } | null
}

export interface DemoDayEvent {
  time_label: string
  /** Closed event_type vocabulary (created, extracted, verified, inject, …). */
  type: string
  link_label: string
  note?: string
  transition?: {
    from: VerificationStatus
    to: VerificationStatus
    to_label?: string
  }
  badge?: VerificationStatus
  /** An inject record's structured payload (T3.20). It was three lines of
   *  prose until 2026-08-11, which meant the mockup and the real branch
   *  rendered the same event from different shapes — the demo could only be
   *  read, never expanded, and the two could disagree without any test
   *  noticing. The fields mirror `inject_journal`'s payload. */
  inject?: DemoInjectDetail
}

export interface DemoInjectDetail {
  tool: string
  context_file: string
  fact_ids: string[]
  article_ids: string[]
  memory_ids: string[]
  budget_tokens: number
  tokens_used: number
  cadence?: string
  trigger?: string
}

export interface DemoDayBucket {
  /** UTC calendar date, YYYY-MM-DD — never the viewer's local day. */
  date: string
  events: DemoDayEvent[]
}

export interface DemoCheckpointEvent {
  time_label: string
  event: "checkpoint_saved" | "resumed"
  detail: string
  tokens_label: string
}

export interface DemoSessionRun {
  id: string
  title: string
  origin_key: string
  project: string
  meta_label: string
  /** null = the run has written no checkpoint yet (honest empty state). */
  latest: {
    saved_label: string
    summary: string
    next_steps: string[]
    key_decisions: string[]
    touched_files: string[]
    resume_block: string
    /** What the resume digest costs against `inject_token_budget`, measured
     *  the way the budget measures (`inject_fill.estimate_tokens`). The real
     *  branch reads the server's `token_estimate`; the fixture carries one so
     *  the mockup shows the same field rather than a blank. */
    token_estimate: number
  } | null
  history: DemoCheckpointEvent[]
}

// ---------------------------------------------------------------------------
// Wave 5 — Settings (S25–S30) + Auth (S31/S32).
// ---------------------------------------------------------------------------

/** The `repo_allowlist` config row (T1.15's SSRF gate input, T1.57
 *  ruling 2's editing surface). Empty patterns = auto-provision inert. */
export interface DemoAllowlistState {
  patterns: string[]
  error?: string
}

export interface DemoFlagsState {
  /** rank_fusion_factor arms: w_conf, w_importance, w_heat, w_recency. */
  fusion_arms: DemoRankArm[]
  /** ppr_enabled, dual_level_enabled, community_injection_enabled. */
  graph_flags: DemoGraphFlag[]
  /** w_context_boost — post-fusion multiplier on a MATCH outcome only. */
  context_boost: DemoRankArm
  corroboration: DemoCorroborationGate
  /** hybrid_search_enabled, reranker_enabled, relation_rescue. */
  behavioral_flags: DemoBehavioralFlag[]
  /** pipeline_concurrency, embedding_batch_size, embedding_concurrency,
   *  entity_cache_ttl_minutes — throughput and cache knobs in the same
   *  `feature_flags` row, which the API has always served and no surface
   *  rendered until 2026-08-21. */
  tunables: DemoTunable[]
  classification_mode: "simple" | "expanded"
  classification_areas: string[]
  repo_allowlist: DemoAllowlistState
  overrides_written: number
}

export interface DemoLLMState {
  purposes: DemoLLMPurpose[]
  /** Code-summarization sub-buckets on the one summarization connection. */
  buckets: DemoCodeBucket[]
  /** Re-homes the dropped ml_profile_ref indirection inline. */
  classifier_kind: "llm" | "local"
  /** Live-reload confirmation after the last save; null until a save. */
  last_save: DemoLLMSaveTrace | null
}

export interface DemoSecurityState {
  blocklisted: number
  lockouts_30d: number
  session: { issued_label: string; jti: string }
  rate_limit: {
    attempt_threshold: number
    lockout_window: string
    ip_source: string
    journaled: string
  }
  cookie_secure: { value: string; note: string }
  tofu: { claimed_label: string; journaled: string }
  /** MCP Host allowlist chips; wild = the explicit "*" opt-out. */
  mcp_hosts: { host: string; wild?: boolean }[]
  /** Dormant Phase-4 ApiKey card — designed, not wired (invariant 23). */
  api_key_scopes: { label: string; never?: boolean }[]
}

export interface DemoMaintenanceState {
  fingerprint: string
  reembed: { memories: number; entities: number; code_chunks: number }
  cleanup: {
    expired: number
    expired_dependents: number
    failures_memory_ingest: number
    failures_code_repo: number
  }
  dbops: {
    retired_fingerprints: string[]
    vacuum_target: string
    vacuum_note: string
    reindex_target: string
    reindex_note: string
  }
  /** Outcome line of the last confirmed op this session; null = none yet. */
  last_op_note: string | null
}

export type DistClientStatus = "connected" | "curbed" | "disconnected"

export interface DemoDistClient {
  id: string
  name: string
  status: DistClientStatus
  handshake: string | null
  context_file: string
  mcp_config: string
  /** "active · last inject 14:12 UTC · 8 items, 1,840/2,000 tokens". */
  push_note: string | null
  curbed_note: string | null
  connect_hint?: string
}

export interface DemoInjectLogRow {
  id: string
  target: string
  event_type: "inject" | "inject_curbed"
  detail: string
  time_label: string
  meta: string
}

export interface DemoInjectItem {
  layer: KnowledgeLayer
  badge: VerificationStatus
  /** "injected as: corroborated" — the label the tool receives. */
  as_label: string
  text: string
}

export interface DemoDistPolicyRow {
  key: string
  value: string
  desc: string
}

export interface DemoDistributionState {
  clients: DemoDistClient[]
  policy: DemoDistPolicyRow[]
  block_preview: string
  log: DemoInjectLogRow[]
  inject_items: DemoInjectItem[]
  watermarks: { key: string; value: string }[]
}

export interface DemoStoreState {
  memories: DemoMemory[]
  repos: Repo[]
  jobs: DemoJob[]
  stats: DashboardStats
  events: ActivityEvent[]
  contributions: ContributionDay[]
  facts: DemoFact[]
  articles: DemoArticle[]
  communities: DemoCommunity[]
  pinSuggestions: DemoPinSuggestion[]
  reviewItems: DemoReviewItem[]
  hygiene: HygieneQueueState
  lastDetectionRun: string
  codeRepos: DemoRepo[]
  codeGraphs: DemoCodeGraph[]
  memoryGraph: DemoMemoryGraph
  chatThreads: DemoChatThread[]
  pipelineRuns: DemoPipelineRun[]
  feedEvents: DemoFeedEvent[]
  pipelineFailures: DemoPipelineFailure[]
  bufferMonitor: DemoBufferMonitor
  dreamMonitor: DemoDreamMonitor
  dreamCycle: DemoDreamCycle
  dreamActions: DemoDreamAction[]
  /** Earlier cycles, past their undo window — every entry undo-blocked. */
  dreamPastActions: DemoDreamAction[]
  dayBuckets: DemoDayBucket[]
  sessionRuns: DemoSessionRun[]
  flags: DemoFlagsState
  gitAccounts: DemoGitAccountsState
  llm: DemoLLMState
  security: DemoSecurityState
  maintenance: DemoMaintenanceState
  distribution: DemoDistributionState
  addMemory: (m: DemoMemory) => void
  updateMemory: (id: string, patch: Partial<DemoMemory>) => void
  deleteMemory: (id: string) => void
  resetMemories: () => void
  ratifyReviewItem: (id: string, ratifiedBy: string) => void
  regroundReviewItem: (id: string) => void
  clearReviewItem: (id: string) => void
  decidePinSuggestion: (id: string, decision: "accepted" | "dismissed") => void
  resolveHygiene: (category: HygieneCategory, ids: string[]) => void
  resetKnowledge: () => void
  triggerReindex: (repoId: string, opts: ReindexOptions) => void
  /** Appends the user message plus a canned demo reply; returns the thread
   *  id (a fresh one when threadId is null). */
  sendChatMessage: (threadId: string | null, content: string) => string
  /** Queues a retry — the row stays open until the pipeline resolves it. */
  retryFailure: (id: string) => void
  retryAllFailures: () => void
  forgetFailure: (id: string) => void
  /** Re-buffers a poison row: back to pending, attempts untouched. */
  retryBufferRow: (id: string) => void
  /** Explicitly forgets a poison row: removed from triage permanently. */
  forgetBufferRow: (id: string) => void
  /** Busy honesty: a trigger on a held lock returns 409 — never queued. */
  triggerJob: (key: string) => JobTriggerResult
  saveJobConfig: (key: string, values: Record<string, number>) => void
  undoDreamAction: (id: string) => void
  /** Undoes only the eligible (not blocked, not already undone) entries. */
  undoDreamBatch: (type: DreamActionType) => void
  resetActivity: () => void
  /** Writes a w_* arm value; the first write flips its source to override. */
  saveArm: (key: string, value: number) => void
  setGraphFlag: (key: string, enabled: boolean) => void
  /** Commit one ladder threshold. `null` clears the commitment and returns
   *  the parameter to its floor — the only way back out of an override. */
  saveCorroboration: (name: string, committed: number | null) => void
  saveTunable: (key: string, value: number) => void
  setClassificationMode: (mode: "simple" | "expanded") => void
  setClassificationAreas: (areas: string[]) => void
  setBehavioralFlag: (key: string, enabled: boolean) => void
  /** Replaces the whole pattern list; validated client-side with the same
   *  host[/path-prefix] shape T1.15's validator accepts. */
  saveRepoAllowlist: (patterns: string[]) => void
  /** Saves a purpose row and records the live-reload confirmation trace. */
  saveLLMPurpose: (
    purpose: LLMPurposeName,
    patch: Partial<Omit<DemoLLMPurpose, "purpose">>,
  ) => void
  saveCodeBucket: (key: DemoCodeBucket["key"], model: string) => void
  setClassifierKind: (kind: "llm" | "local") => void
  dismissLLMSave: () => void
  setJobEnabled: (key: string, enabled: boolean) => void
  saveJobCron: (key: string, cron: string) => void
  /** Confirmed maintenance op — mutates counts and records the outcome. */
  runMaintenanceOp: (op: MaintenanceOpKey) => void
  /** Curbing stops push only; pull is unaffected. Appends an inject_curbed
   *  (or resumed inject) log row and updates the client's watermark. */
  setDistributionCurb: (clientId: string, curbed: boolean) => void
  resetSettings: () => void
}

// Mirrors GitAccountsResponse in use-git-accounts-api.ts. Declared here rather
// than imported: src/demo/data/** may not reach into production modules, and
// the fixture needs a type.
export interface DemoGitAccount {
  id: string
  label: string
  provider: string
  host: string
  username: string
  token_hint: string
  scopes: string | null
  is_default: boolean
  last_verified_at: string | null
  repo_count: number
  created_at: string
  updated_at: string
}

export interface DemoGitForge {
  provider: string
  label: string
  default_host: string
}

export interface DemoGitAccountsState {
  accounts: DemoGitAccount[]
  providers: DemoGitForge[]
}
