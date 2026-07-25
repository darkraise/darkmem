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

export interface DemoStoreState {
  memories: DemoMemory[]
  repos: Repo[]
  jobs: Job[]
  llmProfiles: LlmProfile[]
  stats: DashboardStats
  events: ActivityEvent[]
  contributions: ContributionDay[]
  addMemory: (m: DemoMemory) => void
  updateMemory: (id: string, patch: Partial<DemoMemory>) => void
  deleteMemory: (id: string) => void
  resetMemories: () => void
}
