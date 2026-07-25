export type { Memory, MemoryStatus } from "@/hooks/api"
export type { Repo } from "@/hooks/api"
export type { Job } from "@/hooks/api"
export type { LlmProfile } from "@/hooks/api"

import type { Memory, MemoryStatus, Repo, Job, LlmProfile } from "@/hooks/api"
import type { KnowledgeLayer, VerificationStatus } from "@/components/darkmem"

export interface DashboardStats {
  totalMemories: number
  verifiedFacts: number
  liveArticles: number
  pendingReview: number
  disputedFacts: number
}

export type ActivityEventKind =
  | "memory"
  | "fact"
  | "article"
  | "pipeline"
  | "job"
  | "review"

export interface ActivityEvent {
  id: string
  kind: ActivityEventKind
  title: string
  detail?: string
  verification?: VerificationStatus
  layer?: KnowledgeLayer
  at: string
}

export interface ContributionDay {
  date: string
  count: number
}

export type MemoryRelationType =
  | "CONTRADICTS"
  | "ELABORATES"
  | "DEPENDS_ON"
  | "FOLLOWS"
  | "RELATES_TO"

export interface MemoryRelation {
  rel_type: MemoryRelationType
  memory_id: string
  excerpt: string
}

export type MemoryTimelineEventKind =
  | "created"
  | "extracted"
  | "verified"
  | "superseded"
  | "deprecated"
  | "updated"

export interface MemoryTimelineEvent {
  at: string
  kind: MemoryTimelineEventKind
  description: string
  note?: string
  /** Rung/lifecycle transition rendered as the from→to badge pair.
   *  `from: null` renders the plain "active (no badge)" label. */
  transition?: { from: string | null; to: string }
}

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

export interface DemoMemory extends Memory {
  project: string
  confidence: number
  status: MemoryStatus
  layer: KnowledgeLayer
  verification_status?: VerificationStatus | null
  /** The full honest badge claim, e.g. "supports a fact asserted by…". */
  verification_detail?: string
  /** Optional applies_when declaration, e.g. "env=prod". */
  applies_when?: string | null
  relations?: MemoryRelation[]
  timeline?: MemoryTimelineEvent[]
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
  auto_sync: boolean
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
}

export type CodeNodeKind = "file" | "class" | "method" | "function" | "module"

export interface DemoCodeNode {
  id: string
  name: string
  kind: CodeNodeKind
  file: string
  community: string
}

export interface DemoCodeEdge {
  /** Caller/container side — blast radius walks these in reverse. */
  source: string
  target: string
  type: string
}

export interface DemoCodeCommunity {
  id: string
  label: string
  /** Index into the --chart-N ramp. */
  chart: 1 | 2 | 3 | 4 | 5
}

export interface DemoCodeProcess {
  id: string
  label: string
  /** Ordered node ids. */
  steps: string[]
}

export interface DemoCodeGraph {
  repo_id: string
  nodes: DemoCodeNode[]
  edges: DemoCodeEdge[]
  communities: DemoCodeCommunity[]
  processes: DemoCodeProcess[]
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
  claim: string
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

export interface DemoStoreState {
  memories: DemoMemory[]
  repos: Repo[]
  jobs: Job[]
  llmProfiles: LlmProfile[]
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
}
