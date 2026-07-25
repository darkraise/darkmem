export type { Memory, MemoryStatus } from "@/hooks/api"
export type { Repo } from "@/hooks/api"
export type { Job } from "@/hooks/api"
export type { LlmProfile } from "@/hooks/api"

import type { Memory, Repo, Job, LlmProfile } from "@/hooks/api"
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

export interface DemoStoreState {
  memories: Memory[]
  repos: Repo[]
  jobs: Job[]
  llmProfiles: LlmProfile[]
  stats: DashboardStats
  events: ActivityEvent[]
  contributions: ContributionDay[]
  addMemory: (m: Memory) => void
  deleteMemory: (id: string) => void
  resetMemories: () => void
}
