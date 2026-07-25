import { create } from "zustand"
import memoriesData from "./data/memories.json"
import reposData from "./data/repos.json"
import jobsData from "./data/jobs.json"
import llmProfilesData from "./data/llm-profiles.json"
import { CURATED_MEMORIES } from "./data/memories-curated"
import { enrichBulkMemories, type RawBulkMemory } from "./memories"
import {
  buildActivityFeed,
  buildContributions,
  buildDashboardStats,
} from "./dashboard"
import type { DemoStoreState, DemoMemory, Repo, Job, LlmProfile } from "./types"

const initialMemories: DemoMemory[] = [
  ...CURATED_MEMORIES,
  ...enrichBulkMemories(memoriesData as RawBulkMemory[]),
]

export const useDemoStore = create<DemoStoreState>((set) => ({
  memories: initialMemories,
  repos: reposData as unknown as Repo[],
  jobs: jobsData as unknown as Job[],
  llmProfiles: llmProfilesData as unknown as LlmProfile[],
  stats: buildDashboardStats(initialMemories.length),
  events: buildActivityFeed(),
  contributions: buildContributions(),
  addMemory: (m) =>
    set((s) => ({
      memories: [m, ...s.memories],
      stats: { ...s.stats, totalMemories: s.memories.length + 1 },
    })),
  updateMemory: (id, patch) =>
    set((s) => ({
      memories: s.memories.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    })),
  deleteMemory: (id) =>
    set((s) => {
      const memories = s.memories.filter((x) => x.id !== id)
      return {
        memories,
        stats: { ...s.stats, totalMemories: memories.length },
      }
    }),
  resetMemories: () =>
    set((s) => ({
      memories: initialMemories,
      stats: { ...s.stats, totalMemories: initialMemories.length },
    })),
}))
