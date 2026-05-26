export type { Memory, MemoryStatus } from "@/hooks/api"
export type { Repo } from "@/hooks/api"
export type { Job } from "@/hooks/api"
export type { LlmProfile } from "@/hooks/api"

import type { Memory, Repo, Job, LlmProfile } from "@/hooks/api"

export interface DemoStoreState {
  memories: Memory[]
  repos: Repo[]
  jobs: Job[]
  llmProfiles: LlmProfile[]
  addMemory: (m: Memory) => void
  deleteMemory: (id: string) => void
  resetMemories: () => void
}
